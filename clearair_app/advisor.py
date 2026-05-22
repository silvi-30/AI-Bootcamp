"""
advisor.py — Lógica del asesor "Rocío":

1. Categoriza un valor de PM2.5 según umbrales (basados en guías de la OMS 2021
   y el AQI estadounidense, simplificados a 4 categorías).
2. Construye el banner de calidad (color + título + mensaje breve).
3. Expone `chat_with_rocio()` que llama a la API de Anthropic con el contexto
   del pronóstico ya inyectado. Si no hay API key configurada, cae a un
   modo demo con respuestas locales según el nivel.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# La API de Anthropic se importa de forma perezosa para que la app funcione
# aunque el paquete `anthropic` no esté instalado o no haya API key.
try:
    from anthropic import Anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


# ----------------------------------------------------------------------------
# Categorías de calidad del aire — umbrales OMS 2021
# ----------------------------------------------------------------------------
# Fuente: WHO Global Air Quality Guidelines 2021 (publicadas en septiembre 2021).
# Para PM2.5 (promedio 24h), la OMS define:
#
#   - AQG  (Air Quality Guideline)   :  15 µg/m³   ← guía recomendada
#   - IT-4 (Interim Target 4)        :  25 µg/m³
#   - IT-3 (Interim Target 3)        :  37.5 µg/m³
#   - IT-2 (Interim Target 2)        :  50 µg/m³
#   - IT-1 (Interim Target 1)        :  75 µg/m³   ← objetivo para países muy contaminados
#
# Para la app simplificamos a 4 categorías agrupando los Interim Targets en
# tramos clínicamente significativos:
#
#   < 15  µg/m³  →  Bueno          (por debajo de la guía OMS, aire saludable)
#   < 35  µg/m³  →  Moderado       (entre IT-4 e IT-3, sensibles deben cuidarse)
#   < 75  µg/m³  →  Poco saludable (entre IT-3 e IT-1, riesgo para todos)
#   ≥ 75  µg/m³  →  Peligroso      (por encima del peor Interim Target)
#
# NOTA METODOLÓGICA:
# La OMS define estos cortes sobre PROMEDIOS de 24 horas, no sobre valores
# horarios. Nuestro modelo predice valores horarios, así que estos umbrales
# son una APROXIMACIÓN razonable para una alerta operativa, no un diagnóstico
# clínico. En una versión productiva habría que (a) promediar las 6 horas
# pronosticadas y comparar contra el umbral 24h, o (b) usar los cortes
# horarios de EPA NowCast. Para un MVP es defendible este uso porque
# comunica el orden de magnitud correcto al usuario.

@dataclass(frozen=True)
class AirQualityLevel:
    key: str
    label: str           # texto del banner
    short: str           # etiqueta corta (good/moderate/unhealthy/hazardous)
    color: str           # hex para banner/borde
    bg: str              # hex para fondo del banner
    text: str            # color del texto en banner
    advice: str          # mensaje corto bajo el banner
    number_color: str    # color para el número grande en las tarjetas


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


# Cortes (en µg/m³) — derivados de los umbrales OMS 2021 ver arriba
WHO_GUIDELINE      = 15.0    # AQG
WHO_INTERIM_3      = 35.0    # ~IT-3 redondeado (37.5)
WHO_INTERIM_1      = 75.0    # IT-1


def categorize(pm25: float) -> AirQualityLevel:
    """Devuelve la categoría OMS para un valor de PM2.5 en µg/m³.

    Cortes: 15 / 35 / 75 µg/m³ (ver bloque de documentación arriba).
    """
    if pm25 < WHO_GUIDELINE:
        return GOOD
    elif pm25 < WHO_INTERIM_3:
        return MODERATE
    elif pm25 < WHO_INTERIM_1:
        return UNHEALTHY
    else:
        return HAZARDOUS


def worst_of(values: list[float]) -> AirQualityLevel:
    """Categoría correspondiente al PEOR valor de una lista (para el banner global)."""
    return categorize(max(values))


# ----------------------------------------------------------------------------
# Chat con Rocío
# ----------------------------------------------------------------------------
SYSTEM_PROMPT = """Eres Rocío, una asesora amable y experta en salud respiratoria y \
calidad del aire. Hablas en español, con cercanía pero rigor. Tu trabajo es ayudar al \
usuario a entender el pronóstico de PM2.5 de las próximas 6 horas en su ciudad y darle \
recomendaciones prácticas para protegerse.

Reglas:
- Usa SIEMPRE el pronóstico que el usuario te comparte como contexto. No inventes números.
- Sé concisa: 3 a 6 frases por respuesta, salvo que pidan más detalle.
- Apóyate en los umbrales OMS 2021 para PM2.5 al hacer recomendaciones:
    * < 15 µg/m³  → aire saludable, actividad normal
    * 15–35 µg/m³ → moderado, sensibles deben cuidarse
    * 35–75 µg/m³ → poco saludable para todos, evitar ejercicio al aire libre
    * ≥ 75 µg/m³  → peligroso, quedarse en interiores con purificador
- Si el usuario menciona condiciones de salud (asma, EPOC, embarazo, edad \
avanzada, niños), ajusta las recomendaciones para mayor cuidado: ellos deben \
tratar el siguiente nivel inferior como su umbral.
- Cuando sea relevante para la pregunta, identifica franjas horarias del \
pronóstico con mejores y peores valores para dar consejos accionables \
(ej: "sal a caminar entre las 14:00 y las 15:00 que es lo más limpio").
- No diagnostiques; sugiere consultar a un profesional si hay síntomas.
- No respondas a temas ajenos a calidad del aire / salud respiratoria; redirige amable.
"""


def build_forecast_context(prediction: dict) -> str:
    """Convierte el dict de predicción en un bloque de contexto para el modelo."""
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
        f"Condiciones meteorológicas actuales:",
        f"  - Temperatura: {m['TEMP']:.1f} °C",
        f"  - Punto de rocío: {m['DEWP']:.1f} °C",
        f"  - Presión: {m['PRES']:.0f} hPa",
        f"  - Viento acumulado: {m['Iws']:.1f}",
        f"  - Dirección de viento: {m['cbwd']}",
    ]
    return "\n".join(lines)


def _fallback_reply(user_msg: str, prediction: dict) -> str:
    """Respuesta local cuando no hay API key configurada (modo demo puro)."""
    worst = worst_of([v for _, v in prediction["forecast"]])
    base = {
        "good": (
            "Las próximas 6 horas se mantienen en rango saludable. Puedes hacer "
            "ejercicio al aire libre, salir a caminar y ventilar tu casa con tranquilidad. "
            "Si tienes asma o eres muy sensible, lleva siempre tu inhalador a la mano."
        ),
        "moderate": (
            "El aire estará en rango moderado. Si haces ejercicio intenso, "
            "considera moverlo a interiores o esperar a una franja con valores más bajos. "
            "Personas con asma, embarazadas o niños pequeños deberían reducir el tiempo "
            "al aire libre. Mantén ventanas cerradas si vives cerca de avenidas."
        ),
        "unhealthy": (
            "El pronóstico muestra niveles poco saludables. Te recomiendo evitar "
            "actividad física al aire libre, usar mascarilla N95 si necesitas salir, "
            "y mantener tu casa cerrada con un purificador si tienes uno. "
            "Hidrátate bien y atiende cualquier molestia respiratoria."
        ),
        "hazardous": (
            "⚠️ Niveles peligrosos en el pronóstico. Quédate en interiores tanto como "
            "puedas, sella ventanas y puertas, y usa un purificador de aire con filtro "
            "HEPA si lo tienes. Si necesitas salir, mascarilla N95 bien ajustada es "
            "indispensable. Consulta a un médico si presentas tos, opresión en el pecho "
            "o dificultad para respirar."
        ),
    }[worst.key]
    return base


def chat_with_rocio(
    user_message: str,
    history: list[dict],
    prediction: dict,
) -> str:
    """Envía el mensaje a Claude con el contexto del pronóstico inyectado.

    `history`: lista de mensajes previos en formato [{"role": "user"|"assistant", "content": str}, ...]
    Devuelve el texto de respuesta de Rocío.

    Si no hay API key (variable de entorno ANTHROPIC_API_KEY) o el paquete `anthropic`
    no está disponible, se cae a una respuesta local basada en el nivel pronosticado.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not (_ANTHROPIC_AVAILABLE and api_key):
        return _fallback_reply(user_message, prediction)

    client = Anthropic(api_key=api_key)
    context_block = build_forecast_context(prediction)
    system = (
        SYSTEM_PROMPT
        + "\n\n--- CONTEXTO DEL PRONÓSTICO ACTUAL ---\n"
        + context_block
    )
    # history ya viene con turnos previos; agregamos el nuevo turno del usuario
    messages = history + [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=system,
        messages=messages,
    )
    # Concatenar bloques de texto
    return "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )
