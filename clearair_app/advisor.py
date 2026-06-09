"""
advisor.py — Rocío como RAG con LangChain + LCEL + Redis Cloud.

Mantiene la misma API pública que la versión anterior (categorize, worst_of,
chat_with_rocio, build_forecast_context) para que app.py no requiera cambios.

Cambio importante en esta versión:
- El vector store vive en Redis Cloud (no en disco local), lo que permite que
  Streamlit Community Cloud funcione sin necesidad de commitear datos al repo.
- Necesita dos variables de entorno: GROQ_API_KEY y REDIS_URL.
- Si alguna falla, Rocío usa un fallback local basado en el nivel pronosticado.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# ----------------------------------------------------------------------------
# Carga de credenciales (Streamlit secrets → .env → env var del sistema)
# ----------------------------------------------------------------------------
def _load_secret(name: str) -> str | None:
    """Carga un secreto desde st.secrets si está en Streamlit, sino del env."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and name in st.secrets:
            os.environ[name] = st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name)


# Intentar cargar .env local si existe
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# Empujar Streamlit secrets a env vars
_load_secret("GROQ_API_KEY")
_load_secret("REDIS_URL")


# ----------------------------------------------------------------------------
# Categorías de calidad del aire — umbrales OMS 2021
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class AirQualityLevel:
    key: str
    label: str
    short: str
    color: str
    bg: str
    text: str
    advice: str
    number_color: str


GOOD = AirQualityLevel(
    key="good",
    label="Calidad buena",
    short="good",
    color="#1f9d6a",
    bg="#e3f6ec",
    text="#0f6a45",
    advice=(
        "Por debajo de la guía OMS (15 µg/m³). El aire es seguro: puedes hacer "
        "actividades al aire libre con normalidad."
    ),
    number_color="#1f9d6a",
)
MODERATE = AirQualityLevel(
    key="moderate",
    label="Calidad moderada — precaución",
    short="moderate",
    color="#e8a13b",
    bg="#fdf0e0",
    text="#a05a17",
    advice=(
        "Por encima de la guía OMS pero bajo el Interim Target 3 (37.5 µg/m³). "
        "Ejercicio de alta intensidad no recomendado para personas sensibles."
    ),
    number_color="#e8a13b",
)
UNHEALTHY = AirQualityLevel(
    key="unhealthy",
    label="Calidad poco saludable",
    short="unhealthy",
    color="#d94a3d",
    bg="#fbe4e1",
    text="#8a2a20",
    advice=(
        "Entre los Interim Targets 3 y 1 de la OMS. Evita actividad física al "
        "aire libre. Considera usar mascarilla N95."
    ),
    number_color="#d94a3d",
)
HAZARDOUS = AirQualityLevel(
    key="hazardous",
    label="Calidad peligrosa",
    short="hazardous",
    color="#7a2a8a",
    bg="#efe2f3",
    text="#4a1758",
    advice=(
        "Por encima del peor Interim Target OMS (75 µg/m³). Permanece en "
        "interiores con purificador de aire. Sal solo si es indispensable."
    ),
    number_color="#7a2a8a",
)

WHO_GUIDELINE = 15.0
WHO_INTERIM_3 = 35.0
WHO_INTERIM_1 = 75.0


def categorize(pm25: float) -> AirQualityLevel:
    """Devuelve la categoría OMS para un valor de PM2.5 en µg/m³."""
    if pm25 < WHO_GUIDELINE:
        return GOOD
    elif pm25 < WHO_INTERIM_3:
        return MODERATE
    elif pm25 < WHO_INTERIM_1:
        return UNHEALTHY
    else:
        return HAZARDOUS


def worst_of(values: list[float]) -> AirQualityLevel:
    return categorize(max(values))


# ----------------------------------------------------------------------------
# Construcción del contexto del pronóstico
# ----------------------------------------------------------------------------
def build_forecast_context(prediction: dict) -> str:
    """Convierte el dict de predicción en un bloque de contexto para el LLM."""
    t = prediction["timestamp"]
    lines = [
        f"Hora actual del pronóstico: {t.strftime('%Y-%m-%d %H:%M')}",
        f"PM2.5 actual: {prediction['pm25_now']:.1f} µg/m³ "
        f"({categorize(prediction['pm25_now']).label})",
        "",
        "Pronóstico próximas 6 horas:",
    ]
    for ts, val in prediction["forecast"]:
        cat = categorize(val)
        lines.append(
            f"  - {ts.strftime('%H:%M')}: {val:.0f} µg/m³ ({cat.label})"
        )
    m = prediction["meteo"]
    lines += [
        "",
        "Condiciones meteorológicas actuales:",
        f"  - Temperatura: {m['TEMP']:.1f} °C",
        f"  - Punto de rocío: {m['DEWP']:.1f} °C",
        f"  - Presión: {m['PRES']:.0f} hPa",
        f"  - Viento acumulado: {m['Iws']:.1f}",
        f"  - Dirección de viento: {m['cbwd']}",
    ]
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# RAG con Redis: construcción perezosa de la chain (singleton)
# ----------------------------------------------------------------------------
# Constantes — deben coincidir con el notebook que creó el índice
INDEX_NAME = "rocio_pm25"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
LLM_MODEL = "llama-3.1-8b-instant"

ROCIO_SYSTEM_PROMPT = """Eres Rocío, una asesora amable y experta en salud respiratoria y \
calidad del aire. Hablas en español, con cercanía pero rigor. Tu trabajo es ayudar al \
usuario a entender el pronóstico de PM2.5 y darle recomendaciones prácticas para protegerse.

Reglas:
- Basa SIEMPRE tus recomendaciones en el CONTEXTO DE FUENTES proporcionado. Si el \
contexto no cubre algo, dilo claramente en vez de inventar.
- Usa el PRONÓSTICO ACTUAL para personalizar tu respuesta (no des consejos genéricos).
- Sé concisa: 3 a 6 frases, salvo que pidan más detalle.
- Si el usuario menciona condiciones de salud (asma, EPOC, embarazo, edad avanzada, \
niños), aplica recomendaciones para grupos sensibles: ellos deben tratar el siguiente \
nivel inferior como su umbral.
- Cuando sea útil, identifica franjas horarias del pronóstico con valores mejores/peores.
- No diagnostiques; sugiere consultar a un profesional si hay síntomas preocupantes.
- No respondas a temas ajenos a calidad del aire o salud respiratoria; redirige amable.
"""

ROCIO_USER_TEMPLATE = """CONTEXTO DE FUENTES (OMS, EPA, AirNow):
{context}

PRONÓSTICO ACTUAL DEL USUARIO:
{forecast_context}

PREGUNTA DEL USUARIO:
{question}

Responde como Rocío, en español, basándote en el contexto y personalizando con el pronóstico."""


# Cache global de la chain
_chain = None
_chain_error: str | None = None


def _try_build_chain():
    """Intenta construir la chain RAG conectada a Redis. Devuelve (chain, error_msg)."""
    if not os.environ.get("GROQ_API_KEY"):
        return None, "GROQ_API_KEY no configurada."
    if not os.environ.get("REDIS_URL"):
        return None, "REDIS_URL no configurada."

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_redis import RedisVectorStore, RedisConfig
        from langchain_groq import ChatGroq
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        # Embeddings (locales, se descargan en primer uso)
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # Conexión al vector store ya existente en Redis
        config = RedisConfig(
            index_name=INDEX_NAME,
            redis_url=os.environ["REDIS_URL"],
        )
        vector_store = RedisVectorStore(
            embeddings=embeddings,
            config=config,
        )
        retriever = vector_store.as_retriever(search_kwargs={"k": 4})

        # LLM
        llm = ChatGroq(
            model=LLM_MODEL,
            temperature=0.3,
            max_tokens=600,
        )

        # Prompt + parser
        prompt = ChatPromptTemplate.from_messages([
            ("system", ROCIO_SYSTEM_PROMPT),
            ("user", ROCIO_USER_TEMPLATE),
        ])
        parser = StrOutputParser()

        def format_docs(docs):
            return "\n\n---\n\n".join(d.page_content for d in docs)

        # LCEL chain
        chain = (
            {
                "context": (lambda x: x["question"]) | retriever | format_docs,
                "forecast_context": lambda x: x["forecast_context"],
                "question": lambda x: x["question"],
            }
            | prompt
            | llm
            | parser
        )
        return chain, None

    except Exception as e:
        return None, f"Error construyendo el RAG: {type(e).__name__}: {e}"


def _get_chain():
    """Devuelve la chain ya construida (perezoso + cacheado).

    En Streamlit usa @st.cache_resource (una sola carga por sesión del servidor).
    Fuera de Streamlit usa singleton global.
    """
    global _chain, _chain_error
    if _chain is not None:
        return _chain
    if _chain_error is not None:
        return None  # ya intentamos y falló

    try:
        import streamlit as st

        @st.cache_resource(show_spinner="Cargando a Rocío… (descarga del modelo: ~1-3 min la primera vez)")
        def _build():
            return _try_build_chain()

        chain, err = _build()
    except ImportError:
        chain, err = _try_build_chain()

    if chain is None:
        _chain_error = err
        return None
    _chain = chain
    return _chain


# ----------------------------------------------------------------------------
# Fallback local (si el RAG no está disponible)
# ----------------------------------------------------------------------------
_FALLBACK_BY_LEVEL = {
    "good": (
        "Las próximas 6 horas se mantienen en rango saludable. Puedes hacer "
        "ejercicio al aire libre, salir a caminar y ventilar tu casa con tranquilidad. "
        "Si tienes asma o eres muy sensible, lleva siempre tu inhalador a la mano."
    ),
    "moderate": (
        "El aire estará en rango moderado. Si haces ejercicio intenso, considera "
        "moverlo a interiores o esperar a una franja con valores más bajos. "
        "Personas con asma, embarazadas o niños pequeños deberían reducir el "
        "tiempo al aire libre. Mantén ventanas cerradas si vives cerca de avenidas."
    ),
    "unhealthy": (
        "El pronóstico muestra niveles poco saludables. Te recomiendo evitar "
        "actividad física al aire libre, usar mascarilla N95 si necesitas salir, "
        "y mantener tu casa cerrada con un purificador si tienes uno. Hidrátate "
        "bien y atiende cualquier molestia respiratoria."
    ),
    "hazardous": (
        "⚠️ Niveles peligrosos en el pronóstico. Quédate en interiores tanto como "
        "puedas, sella ventanas y puertas, y usa un purificador HEPA si lo tienes. "
        "Si necesitas salir, mascarilla N95 bien ajustada es indispensable. Consulta "
        "a un médico si presentas tos, opresión en el pecho o dificultad para respirar."
    ),
}


def _fallback_reply(prediction: dict) -> str:
    worst = worst_of([v for _, v in prediction["forecast"]])
    return _FALLBACK_BY_LEVEL[worst.key]


# ----------------------------------------------------------------------------
# API pública: chat_with_rocio
# ----------------------------------------------------------------------------
def chat_with_rocio(
    user_message: str,
    history: list[dict],  # (no usado; mantenido por compatibilidad con app.py)
    prediction: dict,
) -> str:
    """Pregunta a Rocío. Usa el RAG si está disponible; si no, fallback local."""
    chain = _get_chain()
    if chain is None:
        return _fallback_reply(prediction)

    try:
        forecast_context = build_forecast_context(prediction)
        return chain.invoke({
            "question": user_message,
            "forecast_context": forecast_context,
        })
    except Exception as e:
        return (
            f"😅 Tuve un problema técnico al consultarte ({type(e).__name__}). "
            f"Mientras tanto, según el pronóstico:\n\n{_fallback_reply(prediction)}"
        )
