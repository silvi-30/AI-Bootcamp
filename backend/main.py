
# ─────────────────────────────────────────────────────────────────────
# main.py
# Es el servidor de la API. Define los endpoints (URLs) que el sitio
# web puede llamar para hablar con el agente.
#
# Cuando Render arranca el proyecto, ejecuta este archivo.
# ─────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.services.functions import chatear, obtener_historial
from app.services.redismanager import redismanager
import pandas as pd

# ── La aplicación ─────────────────────────────────────────────────────
# Creamos la app FastAPI con metadatos que aparecen en /docs
# /docs es la documentación automática — muy útil para probar la API
app = FastAPI(
    title="Asistente de calidad del Aire PM2.5",
    description="API con pronósticos de PM2.5 y chatbot inteligente sobre contaminación",
    version="1.0.0"
)


# ── CORS ──────────────────────────────────────────────────────────────
# CORS es un mecanismo de seguridad de los navegadores.
# Sin esto, el sitio web no podría llamar la API desde otro dominio.
# allow_origins=["*"] permite llamadas desde cualquier dominio.
# En producción reemplaza ["*"] con el dominio exacto de tu sitio web.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# ── Modelos de datos ──────────────────────────────────────────────────
# Pydantic valida que los datos que llegan y salen tengan
# el formato correcto. Si falta un campo requerido, FastAPI
# retorna un error automáticamente sin que escribamos código extra.

class Consulta(BaseModel):
    """
    Lo que el sitio web envía al endpoint /consultar.

    session_id es opcional:
    - Si no viene → usuario nuevo → generamos un session_id nuevo
    - Si viene    → usuario existente → retomamos su conversación en Redis

    Ejemplo de llamada desde el sitio web:
    {
        "session_id": "abc-123",   (opcional)
        "mensaje": "Me gustan las películas de terror"
    }
    """
    session_id: str | None = None  # opcional — None si es usuario nuevo
    mensaje:    str                # requerido — lo que escribió el usuario


class Respuesta(BaseModel):
    """
    Lo que la API retorna al sitio web.

    El sitio web debe guardar el session_id y enviarlo
    en cada mensaje siguiente para mantener el contexto.

    Ejemplo de respuesta:
    {
        "session_id": "abc-123",
        "respuesta": "Te recomiendo El Conjuro...",
        "mensajes_en_memoria": 4
    }
    """
    session_id:            str  # el sitio web debe guardarlo
    respuesta:             str  # la respuesta del agente
    mensajes_en_memoria:   int  # cuántos mensajes hay en Redis


# ── Prediccion ──────────────────────────────────────────────────
class Prediccion(BaseModel):
    horizonte: str
    pm25: float
    fecha: str

class PrediccionesResponse(BaseModel):
    fecha_inferencia: str
    predicciones: list[Prediccion]


# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/")
def raiz():
    """
    Health check — verifica que la API está activa.
    Render y cualquier sistema de monitoreo pueden llamar
    este endpoint para saber si el servidor está funcionando.
    """
    return {"estado": "activo", "agente": "Asistente de PM2.5 y Calidad del Aire"}


@app.post("/consultar", response_model=Respuesta)
def consultar(consulta: Consulta):
    """
    Endpoint principal — recibe el mensaje y retorna la respuesta.

    Si no viene session_id generamos uno nuevo con uuid4().
    uuid4() crea un ID único de 36 caracteres garantizado.
    El sitio web debe guardar este ID y enviarlo en el próximo mensaje.
    """
    # Si es usuario nuevo generamos su session_id
    session_id = consulta.session_id or str(uuid.uuid4())

    # Llamamos al agente
    resultado = chatear(
        session_id=session_id,
        mensaje=consulta.mensaje
    )

    return Respuesta(
        session_id=          session_id,
        respuesta=           resultado["respuesta"],
        mensajes_en_memoria= resultado["mensajes_en_memoria"]
    )


@app.delete("/limpiar/{session_id}")
def limpiar(session_id: str):
    """
    Borra el historial de un usuario en Redis.
    Útil cuando el usuario quiere empezar una conversación nueva.

    Ejemplo de llamada:
    DELETE https://tu-api.onrender.com/limpiar/abc-123
    """
    obtener_historial(session_id).clear()
    return {"mensaje": f"Historial '{session_id}' eliminado"}


@app.get("/predicciones", response_model=PrediccionesResponse)
def obtener_predicciones():
    """Retorna las 7 predicciones para mostrar en los 7 cuadritos del frontend."""
    ultima_pred = redismanager.obtener_prediction()
    
    if ultima_pred is None or ultima_pred.empty:
        return {"fecha_inferencia": None, "predicciones": []}
    
    row = ultima_pred.iloc[0]
    fecha_inferencia = pd.to_datetime(row['date']).strftime('%Y-%m-%d %H:%M:%S')
    
    predicciones = []
    for h in range(1, 8):
        fecha_pronostico = (pd.to_datetime(row['date']) + pd.Timedelta(hours=h)).strftime('%Y-%m-%d %H:%M:%S')
        predicciones.append(Prediccion(
            horizonte=f"h{h}",
            pm25=float(row[f'pm2.5_(t+{h})']),
            fecha=fecha_pronostico
        ))
    
    return PrediccionesResponse(
        fecha_inferencia=fecha_inferencia,
        predicciones=predicciones
    )