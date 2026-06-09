
# ─────────────────────────────────────────────────────────────────────
# funtion.py
# Contiene toda la lógica del agente: el modelo, la memoria en Redis
# y la función principal que procesa cada mensaje del usuario.
#
# Este archivo es independiente de la API — si mañana cambias FastAPI
# por otro framework, este archivo no necesita modificaciones.
# ─────────────────────────────────────────────────────────────────────

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import RedisChatMessageHistory
from app.services.redismanager import redismanager

# ── El modelo ─────────────────────────────────────────────────────────
# Lo instanciamos una sola vez al arrancar el servidor.
# Si lo creáramos dentro de la función chatear(), se reconectaría
# con Groq en cada mensaje — más lento y más costoso.
modelo = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,   # 0.3 = respuestas consistentes y precisas
    max_tokens=1024     # respuestas detalladas con recomendaciones
)



# ── El template ───────────────────────────────────────────────────────
# Define cómo se arma el prompt antes de enviarlo al modelo.
# Tiene tres partes:
#   1. system            → instrucciones de comportamiento del agente
#   2. MessagesPlaceholder → aquí se insertan los mensajes anteriores de Redis
#   3. human             → el mensaje actual del usuario
#
# Sin MessagesPlaceholder el agente no tendría memoria —
# cada mensaje llegaría al modelo sin contexto previo.

def obtener_contexto_pronostico():
    """
    Lee el último pronóstico de Redis y lo convierte en contexto para el LLM.
    
    Returns:
        str: Contexto formateado o string vacío si no hay datos.
    """
    try:
        ultima_pred = redismanager.obtener_prediction()
        
        if ultima_pred is not None and not ultima_pred.empty:
            fecha_str = ultima_pred.iloc[0]['date']
            fecha = pd.to_datetime(fecha_str).strftime('%Y-%m-%d %H:%M:%S')
            contexto = f"\n\nÚltimo pronóstico de PM2.5 (fecha de inferencia: {fecha}):\n"
            for h in range(1, 8):
                fecha_pronostico = pd.to_datetime(fecha) + timedelta(hours=h)
                valor = ultima_pred.iloc[0][f'pm2.5_(t+{h})']
                contexto += f"- horizonte{h} - {fecha_pronostico}: {valor} µg/m³\n"
            return contexto
    except Exception as e:
        print(f"Error al obtener contexto: {e}")
    
    return ""

def crear_template_dinamico():
    """Crea el template con contexto de pronósticos actualizado."""
    contexto_pronostico = obtener_contexto_pronostico()

    # Hora actual en zona de Bogotá
    ahora = datetime.now(ZoneInfo("America/Bogota")).strftime('%Y-%m-%d %H:%M:%S')
    
    return ChatPromptTemplate.from_messages([
        ("system", f"""Eres un asistente especializado en Material Particulado PM2.5 y salud respiratoria.

Hora actual: {ahora}

Tu rol es:
1. Responder SOLO preguntas relacionadas con PM2.5, calidad del aire y sus efectos en la salud
2. Basarte en información de la OMS, EPA y estudios médicos reconocidos
3. Proporcionar recomendaciones de salud preventiva según niveles de contaminación
4. Contextualizar respuestas con pronósticos disponibles

Información clave:
- PM2.5: partículas ≤2.5 micras, penetran alvéolos pulmonares
- Límites OMS: 15 µg/m³ (24h), 5 µg/m³ (anual)
- Efectos cuando se superan limites: irritación respiratoria, asma, enfermedades cardiovasculares

Pronóstico disponibles:
{contexto_pronostico}

Si pregunta sobre temas NO relacionados, responde: "Solo puedo ayudarte con PM2.5 y calidad del aire. ¿Tienes alguna pregunta sobre contaminación?"

Mantén tono informativo, empático y basado en evidencia científica."""),
        MessagesPlaceholder(variable_name="historial"),
        ("human", "{mensaje}")
    ])

template = crear_template_dinamico()


# ── Ventana de memoria ────────────────────────────────────────────────
# Cuántos mensajes del historial enviamos al modelo en cada llamada.
# 10 mensajes = 5 turnos completos (5 preguntas + 5 respuestas).
# Sin este límite, el historial crecería indefinidamente
# y el costo de tokens subiría con cada mensaje.
VENTANA = 15


def obtener_historial(session_id: str) -> RedisChatMessageHistory:
    """
    Conecta con Redis y retorna el historial de un usuario específico.

    Cada usuario tiene su propio session_id — una clave única que
    identifica su conversación en Redis. Si el usuario es nuevo,
    Redis crea un historial vacío automáticamente.

    ttl=3600 → la conversación se borra si no hay actividad en 1 hora.
    """
    return RedisChatMessageHistory(
        session_id=session_id,
        url=os.environ["REDIS_URL"],  # Render lee esta variable automáticamente
        ttl=3600
    )


def chatear(session_id: str, mensaje: str) -> dict:
    """
    Función principal del agente de PM2.5.
    Recibe el mensaje del usuario y retorna la respuesta.

    Flujo interno:
        1. Lee el historial de este usuario desde Redis
        2. Toma solo los últimos VENTANA mensajes
        3. Arma el prompt y genera la respuesta con el modelo
        4. Guarda el turno nuevo en Redis
        5. Retorna la respuesta con métricas

    Parámetros:
        session_id → identifica al usuario en Redis (única por sesión)
        mensaje    → pregunta o consulta del usuario sobre PM2.5

    Retorna:
        dict con:
        - respuesta: la respuesta del agente
        - session_id: el ID de sesión (para mantener continuidad)
        - mensajes_en_memoria: cantidad de mensajes guardados para este usuario
    """
    
    # ✓ Crea template fresco cada vez
    template = crear_template_dinamico()

    # Paso 1 — traemos el historial de este usuario desde Redis
    historial_redis = obtener_historial(session_id)

    # Paso 2 — aplicamos la ventana: solo los últimos N mensajes para no saturar tokens
    # [-VENTANA:] es Python estándar para "dame los últimos N elementos"
    mensajes_recientes = historial_redis.messages[-VENTANA:]

    # Paso 3 — construimos la chain y generamos la respuesta
    # template  → arma el prompt con contexto, historial y mensaje actual
    # modelo    → genera la respuesta especializada en PM2.5
    # StrOutputParser → convierte la respuesta a texto plano
    chain     = template | modelo | StrOutputParser()
    respuesta = chain.invoke({
        "historial": mensajes_recientes,
        "mensaje":   mensaje
    })

    # Paso 4 — guardamos este turno en Redis para mantener la memoria conversacional
    # En el próximo mensaje, estos dos líneas estarán en el historial disponible
    historial_redis.add_user_message(mensaje)
    historial_redis.add_ai_message(respuesta)

    # Paso 5 — retornamos el resultado
    return {
        "respuesta":           respuesta,
        "session_id":          session_id,
        "mensajes_en_memoria": len(historial_redis.messages)
    }