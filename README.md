# AireVivo 🌿 [Enlace-web](pm25-forecast-agent.netlify.app)
## Monitor Inteligente de PM2.5 en Medellín

[![API Status](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square)](https://ai-bootcamp-czpe.onrender.com)
[![Frontend](https://img.shields.io/badge/Frontend-Deployed-00C7FD?style=flat-square)](https://pm25-forecast-agent.netlify.app)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

**Piloto/MVP** de plataforma para monitoreo y predicción de calidad del aire (PM2.5). 

⚠️ **Estado actual:**
- Prototipo funcional con **datos simulados (DUMMY)** basados en históricos de Beijing (2010-2014)
- NO incluye datos en tiempo real de Medellín
- Modelo XGBoost entrenado con datos de Beijing (validación conceptual del arquitectura)

🎯 **Visión futura:**
- Integración con APIs de datos meteorológicos en tiempo real para Medellín
- Reentrenamiento del modelo con datos reales de Medellín
- Predicciones operacionales para toma de decisiones en salud pública

Utiliza ML (XGBoost) para pronósticos horarios y un asistente de IA (Sofía) para responder consultas sobre contaminación del aire y salud respiratoria.

---

## ⚠️ ESTADO DEL PROYECTO: PILOTO/MVP

```
╔═══════════════════════════════════════════════════════════════════╗
║                      🚧 PILOTO EN DESARROLLO 🚧                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ✅ LO QUE FUNCIONA:                                              ║
║    • Arquitectura completa (API + ML + Chat)                      ║
║    • Predicciones multi-horizonte (XGBoost 7 modelos)             ║
║    • Asistente IA especializado (Sofía)                           ║
║    • Pipeline automatizado cada hora                              ║
║    • Deployment en Render + Netlify                               ║
║                                                                   ║
║  ❌ LO QUE NO ES OPERACIONAL TODAVÍA:                             ║
║    • Datos: DUMMY (no datos reales de Medellín)                   ║
║    • Modelo: Entrenado con datos de Beijing (2010-2014)           ║
║    • Predicciones: Demostrativas (no para toma de decisiones)     ║
║    • Producción: Requiere reentrenamiento con datos reales        ║
║                                                                   ║
║  🎯 PRÓXIMO PASO:                                                 ║
║    Integración de APIs de datos reales (IDEAM, SIATA, DAGMA)      ║
║    + Reentrenamiento modelo con datos de Medellín 2022-2024       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 📸 Características Principales

✨ **Predicciones de PM2.5**
- Pronósticos horarios para 7 horizontes (h+1 a h+7)
- 7 modelos XGBoost entrenados independientemente
- Actualización automática cada hora mediante cron job
- Desescalado de resultados a unidades originales (µg/m³)

🤖 **Asistente Sofía**
- Chatbot especializado en PM2.5 y salud respiratoria
- Alimentado por LLM Groq (Llama 3.3 70B)
- Historial de conversación persistente en Redis
- Respuestas contextualizadas con pronósticos actuales
- Información validada por OMS, EPA y estudios médicos

📊 **Interfaz Intuitiva**
- Panel de control con pronósticos visuales
- Clasificación de calidad del aire (5 niveles)
- Chat en tiempo real con Sofía
- Preguntas frecuentes integradas
- Responsive design (mobile-friendly)

🔄 **Pipeline Automatizado**
- Ingesta de datos cada hora
- Procesamiento de features (one-hot encoding, lags temporales)
- Predicción multi-horizonte
- Almacenamiento en Redis con TTL configurable

---

## 🛠️ Tech Stack

### Backend
| Componente | Tecnología |
|-----------|-----------|
| Framework API | **FastAPI** |
| Servidor | **Uvicorn** |
| ML / Predicción | **XGBoost** |
| Cache / Memory | **Redis** |
| LLM | **Groq** (Llama 3.3 70B) |
| LLM Framework | **LangChain** |
| Procesamiento | **Pandas**, **NumPy** |
| Serialización | **Joblib** |
| Configuración | **Python-dotenv** |

### Frontend
| Componente | Tecnología |
|-----------|-----------|
| Hosting | **Netlify** |
| Arquitectura | HTML/CSS/JavaScript |
| Diseño Responsivo | CSS Grid / Flexbox |

### Infraestructura
---

## 🔄 Arquitectura de Procesos (Crítico entender esto)

AireVivo funciona con **DOS procesos independientes** que NO se comunican directamente:

```
PROCESO 1: CRON JOB (genera datos)
┌─────────────────────────────────────────┐
│ cron.py (ejecuta cada hora)             │
│ ├─ Ingesta de datos                     │
│ ├─ Preparación de features              │
│ ├─ Predicción con 7 modelos XGBoost     │
│ └─ Guarda en Redis                      │
└─────────────────┬───────────────────────┘
                  │ (escribe)
                  ▼
            ┌──────────────┐
            │ Redis Cache  │
            └──────────────┘
                  ▲
                  │ (lee)
┌─────────────────┴───────────────────────┐
│ PROCESO 2: FastAPI (sirve datos)        │
│ main.py (server HTTP)                   │
│ ├─ GET /predicciones                    │
│ ├─ POST /consultar (chat Sofía)         │
│ ├─ DELETE /limpiar                      │
│ └─ GET /                                │
└─────────────────────────────────────────┘
```

### Explicación:

1. **cron.py** es un script que:
   - Se ejecuta UNA VEZ cada hora (vía cron del SO, EasyCron, o GitHub Actions)
   - Genera pronósticos
   - Los escribe en Redis
   - Se termina

2. **FastAPI** es un servidor que:
   - Está SIEMPRE corriendo
   - Lee datos de Redis cuando llegan requests
   - Responde con lo que hay en Redis
   - NO genera predicciones

### En desarrollo:
```bash
Terminal 1: python -m uvicorn main:app --reload
Terminal 2: python cron.py --run  (cuando quieras nuevas predicciones)
```

### En producción (Render):
```
Render ejecuta: uvicorn main:app
EasyCron llama: POST /cron-execute cada hora
```

---

```
AI-Bootcamp/
├── README.md                          # Este archivo
├── backend/
│   ├── main.py                        # Servidor FastAPI y endpoints
│   ├── cron.py                        # Pipeline automático de ingesta y predicción
│   ├── requirements.txt               # Dependencias Python
│   ├── app/
│   │   ├── data/
│   │   │   ├── dummies/              # Datos simulados para desarrollo
│   │   │   │   └── dummies_2026.csv
│   │   │   ├── ingest/               # Datos ingestados (historiales)
│   │   │   │   └── ingest_data.csv
│   │   │   ├── raw/                  # Datos originales
│   │   │   │   └── PRSA_data_2010.1.1-2014.12.31.csv
│   │   │   ├── processed/            # Datos procesados
│   │   │   ├── staging/              # Datos intermedios
│   │   │   └── outputs/              # Resultados
│   │   ├── models/                   # Modelos entrenados (7 XGBoost)
│   │   │   ├── X_scaler.joblib       # Scaler de features
│   │   │   ├── model_xgb_h{1-7}.joblib
│   │   │   ├── y_h{1-7}_scaler.joblib
│   │   │   └── [predicciones y gráficos de validación]
│   │   └── services/
│   │       ├── main.py               # Punto de entrada FastAPI
│   │       ├── functions.py           # Lógica del agente Sofía
│   │       ├── predictor.py          # DataProcessor + Predictor (XGBoost)
│   │       └── redismanager.py       # Gestión de Redis (caché y memoria)
│   └── notebooks/
│       └── train_xgboost_final.ipynb # Entrenamiento de modelos
│       
│
└── frontend/
    └── index.html                    # Interfaz web (HTML/CSS/JS)
```

---

## 🚀 Instalación y Setup

### Requisitos Previos
- Python 3.10+
- pip
- Git
- Cuenta en Groq API (gratuita)
- Redis (local o Render)
- Node.js (opcional, para desarrollo local)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/silvi-30/AI-Bootcamp.git
cd AI-Bootcamp
git checkout deployment
```

### 2. Configurar Backend

#### 2.1 Crear entorno virtual
```bash
cd backend
python -m venv venv

# Activar entorno
# En Linux/Mac:
source venv/bin/activate
# En Windows:
venv\Scripts\activate
```

#### 2.2 Instalar dependencias
```bash
pip install -r requirements.txt
```

#### 2.3 Configurar variables de entorno
Crear archivo `.env` en la carpeta `backend/`:

```bash
# Groq API
GROQ_API_KEY=tu_api_key_groq

# Redis
REDIS_URL=redis://localhost:6379/0

# Opcional: si usas Render o similar
DATABASE_URL=tu_url_redis_remota
```

**Obtener GROQ_API_KEY:**
1. Ir a [console.groq.com](https://console.groq.com)
2. Registrarse (gratuito)
3. Crear API key en Settings
4. Copiar y pegar en `.env`

#### 2.4 Descargar modelos (ya incluidos)
Los modelos XGBoost y scalers están en `app/models/`. Si necesitas reentrenarlos:

```bash
# Ir a notebooks/ y ejecutar de acuerdo con la nueva data
jupyter notebook train_xgboost_final.ipynb
```

### 3. Ejecutar Backend Localmente

⚠️ **IMPORTANTE:** FastAPI y `cron.py` son **procesos independientes**:
- **FastAPI** = API que sirve endpoints, lee datos de Redis
- **cron.py** = Script que genera predicciones y las guarda en Redis (debe ejecutarse cada hora)

Sin `cron.py`, la API no tendrá datos de predicción para mostrar.

---

#### 3.1 FastAPI en desarrollo (Terminal 1)
```bash
# Desde carpeta backend/
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

La API estará en: `http://localhost:8000`  
Documentación interactiva: `http://localhost:8000/docs`

**La API ahora está activa y esperando consultas.**

---

#### 3.2 Ejecutar cron.py manualmente (Terminal 2 - Para desarrollo)

**Abrir una SEGUNDA terminal** en la carpeta `backend/`:

```bash
# Ejecutar el pipeline una sola vez:
python cron.py --run
```

✅ Esto:
- Ingesta datos meteorológicos
- Procesa features
- Genera 7 predicciones (h+1 a h+7)
- Guarda en Redis

📌 **Para desarrollo:** Ejecutar manualmente cada vez que quieras nuevas predicciones.

---

#### 3.3 Programar cron.py automáticamente cada hora (Para producción)

**Opción A: Cron del sistema operativo (Linux/Mac)**
```bash
# Editar crontab:
crontab -e

# Agregar esta línea (ejecuta cada hora en minuto 0):
0 * * * * cd /ruta/completa/a/backend && /usr/bin/python3 cron.py --run >> /tmp/cron.log 2>&1
```

**Verificar que funciona:**
```bash
# Ver logs del cron
tail -f /tmp/cron.log
```

---

**Opción B: Servicio de Cron Externo (Recomendado para desarrollo)**

Si no tienes acceso a crontab o usas Windows:

1. Ir a https://easycron.com (gratuito)
2. Crear cuenta
3. New Cron Job:
   - URL: `https://mi-api.onrender.com/cron-execute`
   - Frequency: `Every hour`
4. Guardar

Esto hará una request HTTP a tu API cada hora.

---

**Opción C: Task Scheduler (Windows)**
```powershell
# En PowerShell (como admin):
$trigger = New-JobTrigger -RepetitionInterval (New-TimeSpan -Hours 1) -RepeatIndefinitely
$action = New-ScheduledTaskAction -ScriptBlock { cd "C:\ruta\backend" ; python cron.py --run }
Register-ScheduledTask -TaskName "AireVivo-Cron" -Trigger $trigger -Action $action
```

### 4. Configurar Frontend

```bash
cd frontend

# Si quieres servir localmente (opcional):
# Con Python 3:
python -m http.server 3000

# Con Node.js:
npx http-server -p 3000
```

Frontend en: `http://localhost:3000`

---

## 📡 API Endpoints

### Health Check
```http
GET /
```
**Response:**
```json
{
  "estado": "activo",
  "agente": "Asistente de PM2.5 y Calidad del Aire"
}
```

---

### Chat con Sofía (Asistente IA)
```http
POST /consultar
```

**Request Body:**
```json
{
  "session_id": "abc-123",  // Opcional — se genera si no existe
  "mensaje": "¿Qué es el PM2.5?"
}
```

**Response:**
```json
{
  "session_id": "abc-123",
  "respuesta": "El PM2.5 son partículas con diámetro ≤2.5 micras...",
  "mensajes_en_memoria": 4
}
```

**Características:**
- Historial persistente por `session_id` en Redis (TTL: 1 hora)
- Ventana de contexto: últimos 15 mensajes
- Responde solo sobre PM2.5 y salud respiratoria
- Proporciona contexto con pronósticos actuales

---

### Obtener Predicciones
```http
GET /predicciones
```

**Response:**
```json
{
  "fecha_inferencia": "2026-06-12 14:00:00",
  "predicciones": [
    {
      "horizonte": "h1",
      "pm25": 32.5,
      "fecha": "2026-06-12 15:00:00"
    },
    {
      "horizonte": "h2",
      "pm25": 35.2,
      "fecha": "2026-06-12 16:00:00"
    }
    // ... h3 a h7
  ]
}
```

---

### Limpiar Historial
```http
DELETE /limpiar/{session_id}
```

**Response:**
```json
{
  "mensaje": "Historial 'abc-123' eliminado"
}
```

**Notas:**
- Elimina la conversación de un usuario
- Útil para pruebas o reinicio de sesión
- El usuario puede generar nuevo `session_id` automáticamente

---

## 🔄 Pipeline de Datos (Cron Job)

El archivo `cron.py` ejecuta automáticamente cada hora:

### 1️⃣ INGESTA
- Lee datos meteorológicos desde `dummies_2026.csv` (datos **SIMULADOS** basados en históricos)
- Crea range horario (última fecha guardada → ahora)
- Guarda en `app/data/ingest/ingest_data.csv`

**⚠️ NOTA:** Los datos son DUMMY/simulados. En producción con datos reales, aquí iría una API call a:
  - OpenWeatherMap
  - NOAA
  - IDEAM (Instituto de Hidrología, Meteorología y Estudios Ambientales - Colombia)
  - Estaciones meteorológicas locales de Medellín

```python
# Ejemplo futuro (reemplazar simulation_download_data):
def ingest_real_data():
    response = requests.get("https://api.weather.service/data")
    return response.json()

dataprocessor.ingest_real_data()  # En lugar de ingest_data_dummy()
```

### 2️⃣ PREPARACIÓN DE FEATURES
- One-hot encoding de variables categóricas (viento: cbwd)
- Extrae mes de la fecha
- Crea lags temporales (7 horizontes)
- Normaliza con `X_scaler.joblib`

```python
date, df = dataprocessor.features_for_inferece()
```

### 3️⃣ PREDICCIÓN
- 7 modelos XGBoost (uno por horizonte h+1 a h+7)
- Desescala resultados con `y_h{1-7}_scaler.joblib`
- Retorna predicciones en µg/m³

```python
prediction = predictor.predict_pm25(date, df)
```

### 4️⃣ ALMACENAMIENTO
- Guarda en Redis como Sorted Set
- TTL: 7 horas
- Clave: `prediction:y_prediction`

```python
redismanager.guardar_prediction(datos)
```

---

## 🤖 Asistente Sofía (LLM Agent)

### Características Técnicas

**Modelo:** Llama 3.3 70B (vía Groq API)  
**Framework:** LangChain  
**Memoria:** Redis (RedisChatMessageHistory)  
**Temperature:** 0.3 (respuestas precisas y consistentes)  
**Max tokens:** 1024 (respuestas detalladas)

### Sistema de Prompts

El agente opera con un template dinámico que incluye:

1. **Instrucciones del sistema**
   - Especialización en PM2.5 y salud respiratoria
   - Basarse en OMS, EPA y estudios médicos
   - Hora actual y zona horaria

2. **Contexto de pronósticos**
   - Últimas 7 predicciones desde Redis
   - Actualización dinámica antes de cada respuesta

3. **Historial conversacional**
   - Últimos 15 mensajes del usuario
   - Mantiene coherencia conversacional
   - TTL: 1 hora (auto-cleanup en Redis)

4. **Mensaje actual**
   - Consulta del usuario

### Flujo de una Conversación

```
1. Usuario envía mensaje → POST /consultar
2. Genera/obtiene session_id
3. Recupera historial desde Redis
4. Toma últimos 15 mensajes (ventana de contexto)
5. Obtiene últimos pronósticos
6. Crea prompt dinámico
7. Llama a Groq API
8. Obtiene respuesta
9. Guarda turno (user + AI) en Redis
10. Retorna respuesta con métricas
```

---

## 🌐 Deployment

### Backend → Render

**Plataforma:** Render (render.com)  
**Tipo:** Web Service  
**URL:** https://ai-bootcamp-czpe.onrender.com

#### Paso 1: Conectar repositorio
1. Ir a [render.com](https://render.com)
2. Login con GitHub
3. New → Web Service
4. Seleccionar repositorio `AI-Bootcamp`
5. Rama: `deployment`

#### Paso 2: Configuración
```
Build Command:     cd backend && pip install -r requirements.txt
Start Command:     cd backend && uvicorn main:app --host 0.0.0.0 --port 8000
Root Directory:    ./
```

#### Paso 3: Variables de entorno en Render
En la sección "Environment":
```
GROQ_API_KEY=tu_api_key
REDIS_URL=redis://tu-redis-host:puerto/0
```

#### Paso 4: Ejecutar cron.py en producción ⚠️ IMPORTANTE

**El problema:** En Render, solo puedes tener UN proceso principal (la API FastAPI). El `cron.py` NO se ejecutará automáticamente.

**La solución:** Usar un scheduler EXTERNO que haga un HTTP request a tu API cada hora.

**Crear un endpoint en FastAPI para ejecutar cron:**

Editar `backend/main.py` y agregar:
```python
from cron import run as run_cron

@app.post("/cron-execute")
def cron_execute():
    """Endpoint para ejecutar el pipeline de predicción desde un scheduler externo."""
    try:
        run_cron()
        return {"status": "success", "message": "Pipeline ejecutado"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
```

**Configurar scheduler externo (EasyCron.com):**

1. Ir a https://easycron.com (gratuito)
2. Sign up
3. Crear Cron Job:
   - URL: `https://ai-bootcamp-czpe.onrender.com/cron-execute`
   - HTTP Method: `POST`
   - Cron Expression: `0 * * * *` (cada hora)
4. Guardar

✅ Ahora el pipeline se ejecutará automáticamente cada hora.

**Alternativa: GitHub Actions** (también gratuito)

Crear `.github/workflows/cron.yml`:
```yaml
name: Daily Cron Job

on:
  schedule:
    - cron: '0 * * * *'  # Cada hora

jobs:
  cron:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger cron endpoint
        run: |
          curl -X POST https://ai-bootcamp-czpe.onrender.com/cron-execute
```

---

### Frontend → Netlify

**Plataforma:** Netlify (netlify.com)  
**URL:** https://pm25-forecast-agent.netlify.app

#### Paso 1: Conectar repositorio
1. Ir a [netlify.com](https://netlify.com)
2. Login con GitHub
3. New site from Git
4. Seleccionar `AI-Bootcamp`
5. Branch: `deployment`
6. Base directory: `frontend/`

#### Paso 2: Configuración Build
```
Build command: (dejar en blanco — solo HTML/CSS/JS)
Publish directory: frontend/
```

#### Paso 3: Variables de entorno (si aplica)
En Netlify → Site settings → Environment:
```
REACT_APP_API_URL=https://ai-bootcamp-czpe.onrender.com
```

Actualizar `frontend/index.html` para usar esta variable:
```javascript
const API_URL = process.env.REACT_APP_API_URL || 'https://ai-bootcamp-czpe.onrender.com';
```

#### Paso 4: Deploy
- Cada push a `deployment` → deploy automático
- Historial y rollback disponible en Netlify dashboard

---

## 🧪 Pruebas Locales

### 1. Verificar API
```bash
curl http://localhost:8000/

# Respuesta esperada:
# {"estado":"activo","agente":"Asistente de PM2.5..."}
```

### 2. Consultar asistente
```bash
curl -X POST http://localhost:8000/consultar \
  -H "Content-Type: application/json" \
  -d '{"mensaje": "¿Qué es el PM2.5?"}'
```

### 3. Obtener pronósticos
```bash
curl http://localhost:8000/predicciones
```

### 4. Ejecutar pipeline completo
```bash
python cron.py --run
```

### 5. Documentación interactiva
Ir a: `http://localhost:8000/docs`  
(Swagger UI automático de FastAPI)

---

## 📊 Modelos Machine Learning

### ⚠️ Estado Actual (Piloto)

**Tipo:** Multi-output XGBoost  
**Horizontes:** 7 (h+1 a h+7)  
**Modelos:** 7 XGBoost independientes  
**Features:** 53 (variables + lags + dummies)

**❗ IMPORTANTE:** 
- Modelo entrenado con datos de **Beijing (2010-2014)**, NO de Medellín
- Usado para validar arquitectura y concepto
- Las predicciones actuales son **demostrativas**, no operacionales
- Requiere reentrenamiento con datos reales de Medellín

### Variables de Entrada

**Meteorológicas:**
- TEMP (Temperatura)
- DEWP (Punto de rocío)
- PRES (Presión)
- Iws (Velocidad del viento)
- Is (Radiación solar)
- Ir (Radiación infrarroja)
- cbwd (Dirección del viento)

**Objetivo:**
- PM2.5 (actual + lags de 7 horas)

### Features Engineered

- **One-hot encoding:** cbwd → cbwd_NE, cbwd_NW, cbwd_SE, cbwd_cv
- **Temporal:** month_1 a month_12
- **Lags:** 7 horizontes previos de PM2.5, TEMP, DEWP, PRES, Iws

### Datos de Entrenamiento

**Dataset:** PRSA (Beijing Air Quality Data)  
**Rango:** 2010-01-01 a 2014-12-31  
**Frecuencia:** Horaria  
**Localización:** Beijing, China (NO Medellín)

**Preprocessing:**
- Llenado de faltantes (forward-fill)
- Normalización con StandardScaler
- Train/test split: 80/20

### 🚀 Roadmap: Reentrenamiento con datos de Medellín

Para pasarlo a producción operacional:

1. **Recolectar datos reales de Medellín:**
   - PM2.5 real: Estaciones de IDEAM, DAGMA, SIATA
   - Variables meteorológicas: OpenWeatherMap, NOAA
   - Mínimo 1-2 años de históricos

2. **Reentrenar modelo:**
   ```bash
   cd notebooks/
   jupyter notebook train_xgboost_final.ipynb
   # Cambiar dataset_path → datos_medellin.csv
   # Ejecutar pipeline completo
   ```

3. **Validación:**
   - Evaluar métricas con datos de Medellín
   - Test en producción con período de observación
   - Ajustar hyperparameters según comportamiento local

4. **Desplegar:**
   ```bash
   # Actualizar modelos en app/models/
   git push
   # Render redeploy automáticamente
   ```

---

## 🔐 Variables de Entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `GROQ_API_KEY` | API key de Groq | `gsk_...` |
| `REDIS_URL` | Conexión a Redis | `redis://localhost:6379/0` |
| `REACT_APP_API_URL` | URL del backend (frontend) | `https://api.example.com` |

**Archivo `.env` (backend):**
```bash
# Groq
GROQ_API_KEY=gsk_tu_api_key_aqui

# Redis (local para dev)
REDIS_URL=redis://localhost:6379/0

# Redis (Render en producción)
# REDIS_URL=redis://default:password@host:port
```

---

## 🐛 Troubleshooting

### Error: "Connection refused" (Redis)
**Causa:** Redis no está corriendo  
**Solución:**
```bash
# Verificar si Redis está activo
redis-cli ping

# Si no está, instalar y ejecutar:
# Linux/Mac: brew install redis && redis-server
# Windows: Descargar de memurai.com o usar WSL
```

### Error: "GROQ_API_KEY not found"
**Causa:** Variable de entorno no configurada  
**Solución:**
```bash
# Crear .env en backend/
echo "GROQ_API_KEY=tu_clave" > backend/.env
```

### Frontend no conecta con API
**Causa:** CORS o URL incorrecta  
**Solución en frontend/index.html:**
```javascript
// Verificar URL
const API_URL = 'https://ai-bootcamp-czpe.onrender.com';
console.log('Conectando a:', API_URL);
```

### Las predicciones son None o vacías
**Causa:** El cron job NO se ha ejecutado todavía  
**Solución:**
```bash
# En desarrollo, ejecutar manualmente en terminal 2:
cd backend && python cron.py --run

# En producción, verificar que:
# 1. El scheduler externo (EasyCron/GitHub Actions) está activo
# 2. Hacer un test manual:
curl -X POST https://ai-bootcamp-czpe.onrender.com/cron-execute

# 3. Verificar en Redis:
redis-cli GET "prediction:y_prediction"
```

**Si sigue retornando None:**
```bash
# Ver logs del cron en local:
python cron.py --run

# Verificar que hay datos en ingest_data.csv:
head app/data/ingest/ingest_data.csv
```

---

## 📚 Documentación Adicional

- **FastAPI:** https://fastapi.tiangolo.com/
- **XGBoost:** https://xgboost.readthedocs.io/
- **LangChain:** https://docs.langchain.com/
- **Groq API:** https://console.groq.com/docs
- **Redis:** https://redis.io/documentation
- **Render Deployment:** https://render.com/docs

---

## 🤝 Contribuir

Las contribuciones son bienvenidas! Para colaborar:

1. Fork el repositorio
2. Crear rama: `git checkout -b feature/tu-feature`
3. Commit cambios: `git commit -m 'Add: tu-feature'`
4. Push: `git push origin feature/tu-feature`
5. Abrir Pull Request

**Áreas de mejora:**
- [ ] Agregar más modelos de predicción
- [ ] Expandir capacidades del asistente Sofía
- [ ] Integrar datos en tiempo real
- [ ] Mejorar UI/UX del frontend
- [ ] Tests unitarios y E2E
- [ ] Documentación de API en OpenAPI

---

## 📝 Licencia

Este proyecto está bajo la licencia **MIT**. Ver archivo `LICENSE` para más detalles.

---

## 👥 Autores

- **Silvina y Carlos** — Desarrollo, modelos ML, deployment
- **Equipo TALENTO TECH - AI-Bootcamp** — Mentoría y guía

---

## 📧 Contacto y Soporte

Para preguntas o issues:
- Abrir issue en GitHub

---

## 🎯 Roadmap Futuro

### Fase 1: Integración de Datos en Tiempo Real (MVP → Producción)
- ✅ Arquitectura base (FastAPI + XGBoost + Redis)
- ✅ Asistente Sofía (LLM agent)
- 📋 **Integración IDEAM/SIATA** - Datos meteorológicos reales de Medellín
- 📋 **Integración estaciones PM2.5** - Datos reales de contaminación
- 📋 **Reentrenamiento modelo** - XGBoost con datos de Medellín 2022-2024
- 📋 **Validación operacional** - Período de prueba 2-3 meses

### Fase 2: Características Avanzadas
- 📋 Dashboard avanzado con gráficos interactivos (Plotly, Grafana)
- 📋 Exportación de datos y reportes (PDF, CSV)
- 📋 Notificaciones push de alertas (cuando PM2.5 > umbrales)
- 📋 Integración con sistemas de salud pública

### Fase 3: Escalabilidad
- 📋 Multi-ciudad (Cali, Bogotá, etc)
- 📋 Mobile app (iOS/Android)
- 📋 Multi-idioma (EN, ES, FR)
- 📋 API pública para terceros

---

## 📝 Notas Técnicas Importantes

### Limitaciones Actuales (Piloto)
1. **Modelo:** Entrenado con datos de Beijing → NO aplicable directamente a Medellín
2. **Datos:** DUMMY simulados → NO datos reales
3. **Predicciones:** Demostrativas/conceptuales → NO operacionales
4. **Cobertura:** Solo prototipo web → Sin mobile aún
5. **Confiabilidad:** Depende de reentrenamiento con datos reales

### Consideraciones para Implementación Real

**Cuando integres datos reales de Medellín:**

1. **Fuentes de datos recomendadas:**
   - **IDEAM** (www.ideam.gov.co) - Datos meteorológicos nacionales
   - **SIATA** (www.siata.gov.co) - Sistema de alerta temprana de Medellín
   - **DAGMA** (dagma.gov.co) - Monitoreo de calidad del aire en Medellín
   - **OpenWeatherMap API** - Datos complementarios en tiempo real

2. **Pipeline de datos:**
   ```
   API IDEAM/SIATA → Validación → Normalización → Predicción → Redis → Frontend
   ```

3. **Reentrenamiento periódico:**
   - Cada 3-6 meses con nuevos datos
   - Evaluación de drift del modelo
   - Actualización de scalers si es necesario

4. **Monitoreo en producción:**
   - Métricas de predicción (RMSE, MAE)
   - Cobertura de datos (% de horas sin faltantes)
   - Latencia de predicción
   - Error de predicción vs datos observados

5. **Compliance:**
   - Privacidad de datos (GDPR, LSPDP Colombia)
   - Acceso a APIs autorizadas
   - Documentación de calibración de sensores

---

**Última actualización:** Junio 2026  
**Rama:** `deployment`  
**Estado:** 🟢 Activo en producción.
