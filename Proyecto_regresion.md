# Proyecto de Regresión / Pronóstico con Beijing PM2.5 (UCI)

**Dataset:** Beijing PM2.5 Data (UCI)  
https://archive.ics.uci.edu/dataset/381/beijing+pm2+5+data

## 1) Objetivo del proyecto

Construir un sistema para **predecir** y/o **pronosticar** la concentración de **PM2.5** (target) usando variables meteorológicas y temporales.

Dos enfoques posibles (se pueden hacer ambos):
1. **Regresión supervisada (one-step)**: predecir `pm2.5` en el mismo timestamp usando variables exógenas (TEMP, PRES, DEWP, etc.) y features de tiempo.
2. **Pronóstico (forecasting)**:
   - **One-step-ahead**: predecir `pm2.5(t+1)` usando información hasta `t`.
   - **Multi-step**: predecir `pm2.5(t+h)` para varios horizontes `h` (p.ej. 6h, 24h).

**Métrica sugerida (regresión):** MAE, RMSE, MAPE/SMAPE (cuidado si hay ceros), R².  
**Métrica sugerida (series de tiempo):** MAE/RMSE por horizonte, error acumulado por ventana temporal.

---

## 2) Entendimiento de datos (EDA)

### 2.1 Variables típicas del dataset
Suele incluir:
- `pm2.5` (target)
- Variables meteorológicas: `DEWP`, `TEMP`, `PRES`, `cbwd` (dirección del viento), `Iws` (velocidad acumulada), `Is`, `Ir`
- Variables de fecha/hora: año, mes, día, hora (o timestamp)
- Estación (si aplica): por ejemplo `station` o similar (si el dataset viene en variantes)

### 2.2 Preguntas guía para EDA
- ¿Cómo se distribuye `pm2.5`? ¿Hay colas largas/outliers?
- ¿Existen patrones diarios/semanales/estacionales?
- ¿Qué correlaciones hay entre `pm2.5` y variables meteorológicas?
- ¿Hay cambios de régimen (años con diferente comportamiento)?
- ¿Faltantes por columnas y por periodos de tiempo (bloques)?

### 2.3 Visualizaciones recomendadas
- Serie temporal de `pm2.5` (global y por año/mes)
- Boxplots de `pm2.5` por hora del día, por mes
- Heatmap de correlación (incluyendo lags)
- Distribución y QQ-plot (si se evalúa transformación log)
- Mapa de faltantes (missingness matrix)

---

## 3) Calidad de datos (Data Quality)

### 3.1 Chequeos mínimos
- **Tipos**: numéricos vs categóricos (`cbwd`)
- **Rangos plausibles**: TEMP, PRES, DEWP, etc.
- **Duplicados**: timestamps repetidos
- **Orden temporal**: continuidad de timestamps (saltos)
- **Outliers**: picos extremos; decidir si se recortan, transforman o se modelan robustamente
- **Consistencia**: valores imposibles (negativos donde no corresponde)

### 3.2 Reglas específicas para series temporales
- Evitar **data leakage**: toda imputación/normalización debe ajustarse **solo con train** y aplicarse a val/test.
- Respetar el tiempo: splits por fecha, no random split.

---

## 4) Manejo de faltantes (Missing Data)

### 4.1 Análisis de faltantes
- Porcentaje por columna
- Patrones: ¿faltan bloques completos de tiempo?
- ¿Faltan más en ciertas épocas o estaciones?

### 4.2 Estrategias de imputación (recomendadas)
**Para variables meteorológicas:**
- Forward fill / backward fill (con cuidado en gaps largos)
- Interpolación temporal (lineal) para gaps cortos
- Model-based imputation (opcional): KNNImputer o modelos simples por variable

**Para `pm2.5` (target):**
- Si el target falta en train:
  - Opción A: eliminar esas filas de entrenamiento
  - Opción B: imputar solo para features derivados (p.ej. lags) pero **no** usar target imputado como verdad
- En forecasting con lags, si faltan valores en historial, definir reglas claras (p.ej. ventanas mínimas).

**Regla práctica:**
- Gaps cortos: interpolación/ffill
- Gaps largos: considerar segmentar, o marcar con flags y evitar inventar señal

### 4.3 Features auxiliares para faltantes
- `is_missing_<col>` (banderas)
- `gap_length` (si se detecta longitud del hueco)

---

## 5) Ingeniería de características (Feature Engineering)

### 5.1 Features temporales
- `hour`, `dayofweek`, `month`
- Codificación cíclica: `sin(2π*hour/24)`, `cos(2π*hour/24)` (similar para mes)
- Festivos (si se agrega un calendario; opcional)

### 5.2 Lags y ventanas (para pronóstico)
- Lags de `pm2.5`: `t-1`, `t-3`, `t-6`, `t-12`, `t-24`, etc.
- Rolling statistics: media móvil, mediana, std en ventanas (6h, 24h, 7d)
- Lags para exógenas: TEMP(t-1), PRES(t-1), etc. (opcional)
- Tendencia: diferencia `pm2.5(t) - pm2.5(t-1)` (si procede)

### 5.3 Categóricas
- `cbwd` (dirección): one-hot encoding
- `station` (si existe): one-hot o embeddings (según modelo)

### 5.4 Transformaciones
- `log1p(pm2.5)` para estabilizar varianza (evaluar impacto en métricas)
- Robust scaling (si hay outliers)

---

## 6) Definición de splits (Train/Val/Test) y validación

### 6.1 Split temporal recomendado
- Train: años iniciales
- Validación: año intermedio
- Test: último año (o últimos meses)

Ejemplo conceptual:
- Train: 2010–2013
- Val: 2014
- Test: 2015

### 6.2 Validación tipo rolling / walk-forward
- Ventana deslizante que re-entrena o expande train con el tiempo
- Especialmente útil para comparar modelos de forecasting

---

## 7) Modelado

### 7.1 Baselines indispensables
- **Persistencia**: `pm2.5(t+1) = pm2.5(t)` (para forecasting)
- Media móvil simple (p.ej. 24h)
- Regresión lineal / Ridge / Lasso

### 7.2 Modelos clásicos (tabular)
- Random Forest / ExtraTrees
- Gradient Boosting (XGBoost/LightGBM/CatBoost si está permitido)
- SVR (si el tamaño lo permite)

### 7.3 Modelos orientados a secuencia (opcional)
- LSTM/GRU/TCN
- Transformer para series (si se desea)

**Recomendación práctica para bootcamp:**
- Empezar con Ridge + features temporales + lags
- Luego Gradient Boosting con tuning moderado

### 7.4 Consideraciones de tuning
- No usar CV aleatoria; usar **TimeSeriesSplit** o walk-forward.
- Minimizar overfitting con regularización, early stopping (si aplica).

---

## 8) Evaluación y explicabilidad

### 8.1 Métricas
- MAE y RMSE (principales)
- R² (como apoyo)
- Métricas por segmento: por hora del día, por estación del año, por rangos de PM2.5

### 8.2 Diagnóstico de errores
- Error vs nivel de PM2.5 (¿falla en picos?)
- Error por condiciones meteorológicas (TEMP alto/bajo, etc.)
- Residuales autocorrelacionados (ACF/PACF de residuales)

### 8.3 Explicabilidad
- Importancia de features (GBMs)
- Permutation importance
- SHAP (si se quiere profundidad)

---

## 9) Pipeline reproducible (MLOps “ligero”)

### 9.1 Estructura recomendada del proyecto
- `data/` (crudo, intermedio, procesado) *(idealmente ignorar en git si es grande)*
- `notebooks/` (EDA y prototipos)
- `src/`
  - `data/` (ingesta, limpieza, features)
  - `models/` (entrenamiento, evaluación)
  - `inference/` (predicción, API)
- `docs/` (este documento + reportes)
- `tests/` (smoke tests de pipeline)
- `requirements.txt` o `pyproject.toml`

### 9.2 Versionado
- Guardar:
  - versión del dataset (o script de descarga)
  - config de entrenamiento
  - artefactos (modelo + scaler/encoder) con fecha/commit hash

---

## 10) Puesta en marcha (Deployment)

### 10.1 Modos de inferencia
- **Batch**: pronóstico diario/horario para un rango de fechas
- **Online**: API REST (FastAPI) que recibe features y retorna predicción
- **Streaming** (opcional): si llegan sensores en tiempo real

### 10.2 Contrato de entrada/salida
- Entrada: timestamp + variables meteorológicas + (opcional) historial para lags
- Salida: `pm2.5_pred`, intervalos de confianza (opcional)

### 10.3 Monitoreo
- Data drift (distribución de TEMP/PRES/DEWP)
- Performance drift (MAE en producción)
- Alertas por faltantes o gaps

---

## 11) Extensión: Integración con un enfoque RAG (Retrieval-Augmented Generation)

> Nota: RAG no suele “mejorar” directamente una regresión numérica, pero **sí** es útil para:
> - Documentar y explicar predicciones (explicación contextual).
> - Responder preguntas sobre el dataset y el pipeline.
> - Ayudar a analistas/usuarios a interpretar resultados y diagnósticos.
> - Soportar troubleshooting del flujo (calidad, faltantes, drift).

### 11.1 Qué “conocimiento” recuperar
- Diccionario de datos (descripción de columnas)
- Reglas de limpieza e imputación aplicadas
- Reportes de EDA (resúmenes mensuales, picos, eventos)
- Model card (métricas, limitaciones, sesgos)
- Resultados de evaluación por periodo/horizonte
- Logs de monitoreo y drift

### 11.2 Documentos a indexar (ejemplos)
- `docs/data_dictionary.md`
- `docs/eda_report.md`
- `docs/model_card.md`
- `docs/monitoring_runbooks.md`
- Tablas agregadas: estadísticos por mes/hora

### 11.3 Flujo RAG propuesto (alto nivel)
1. Usuario pregunta: “¿Por qué el pronóstico sube mañana?”
2. Retriever busca:
   - Importancias/SHAP para el rango temporal
   - Comparables históricos (días similares)
   - Reglas de imputación aplicadas (si hubo faltantes)
3. Generador (LLM) responde:
   - Explicación con evidencia (citas a documentos)
   - Recomendaciones (p.ej. revisar gaps)

### 11.4 Output recomendado del sistema RAG
- Respuesta en lenguaje natural + referencias a:
  - periodos y features influyentes
  - calidad de datos del tramo
  - métricas esperadas para ese contexto

---

## 12) Entregables finales sugeridos

1. Notebook EDA (`notebooks/01_eda_pm25.ipynb`)
2. Pipeline de preparación (`src/data/make_dataset.py`)
3. Entrenamiento y evaluación (`src/models/train.py`, `src/models/evaluate.py`)
4. Artefactos versionados (modelo + preprocesadores)
5. Documento “Model Card” (`docs/model_card.md`)
6. (Opcional) API de inferencia (`src/inference/api.py`)
7. (Opcional) Módulo RAG con índice y documentos (`docs/` + scripts)

---

## 13) Riesgos y buenas prácticas

- **Leakage temporal**: no mezclar futuro en features.
- **Imputación agresiva**: no “inventar” target; preferir reglas conservadoras.
- **Métricas engañosas**: evaluar por segmentos y picos (alta contaminación).
- **Cambios de distribución**: monitorear drift año a año.

---

## 14) Referencias

- UCI: Beijing PM2.5 Data  
  https://archive.ics.uci.edu/dataset/381/beijing+pm2+5+data
- Buenas prácticas time series: splits temporales, walk-forward.
- Documentación de model cards y monitoreo (recomendado para producción).
