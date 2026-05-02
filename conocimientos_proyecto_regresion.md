# Conocimientos necesarios para el Proyecto de Regresión PM2.5

---

## 1. Modelos de Machine Learning

### Baselines
- **Persistencia** (naive forecast): `pm2.5(t+1) = pm2.5(t)`
- **Media móvil simple**
- **Regresión Lineal** (scikit-learn: `LinearRegression`)
- **Ridge / Lasso** (regularización L2/L1 — `Ridge`, `Lasso` en scikit-learn)

### Modelos clásicos tabulares
- **Random Forest** (`RandomForestRegressor`)
- **ExtraTrees** (`ExtraTreesRegressor`)
- **Gradient Boosting** (`GradientBoostingRegressor` de scikit-learn)
- **XGBoost** (`xgboost`)
- **LightGBM** (`lightgbm`)
- **CatBoost** (`catboost`) *(opcional)*
- **SVR** — Support Vector Regression (`sklearn.svm.SVR`)

### Modelos de series temporales / secuencias (opcional/avanzado)
- **LSTM** — Long Short-Term Memory (PyTorch o TensorFlow/Keras)
- **GRU** — Gated Recurrent Unit (PyTorch o TensorFlow/Keras)
- **TCN** — Temporal Convolutional Network
- **Transformer para series temporales** (Informer, PatchTST, etc.)

---

## 2. Librerías principales de Python

### Manipulación y análisis de datos
| Librería | Uso |
|---|---|
| `pandas` | Carga, limpieza, manipulación de series temporales |
| `numpy` | Operaciones numéricas, arrays |

### Visualización
| Librería | Uso |
|---|---|
| `matplotlib` | Gráficas base (series, residuales) |
| `seaborn` | Heatmaps de correlación, boxplots, distribuciones |
| `missingno` | Mapa visual de valores faltantes |
| `plotly` *(opcional)* | Gráficas interactivas |

### Machine Learning
| Librería | Uso |
|---|---|
| `scikit-learn` | Modelos lineales, Random Forest, SVR, pipelines, métricas, escalado, imputación, `TimeSeriesSplit` |
| `xgboost` | Gradient Boosting optimizado |
| `lightgbm` | Gradient Boosting eficiente en memoria |
| `catboost` *(opcional)* | Gradient Boosting con manejo nativo de categóricas |

### Deep Learning (opcional/avanzado)
| Librería | Uso |
|---|---|
| `torch` (PyTorch) | LSTM, GRU, Transformers para series |
| `tensorflow` / `keras` | Alternativa para LSTM/GRU |

### Series de tiempo
| Librería | Uso |
|---|---|
| `statsmodels` | ACF/PACF de residuales, diagnósticos estadísticos |
| `sktime` *(opcional)* | Framework para forecasting con scikit-learn API |

### Explicabilidad
| Librería | Uso |
|---|---|
| `shap` | SHAP values para interpretación de modelos |
| `eli5` *(opcional)* | Permutation importance |

### MLOps y versionado
| Librería | Uso |
|---|---|
| `joblib` *(preferido)* / `pickle` *(solo para artefactos de confianza)* | Serialización de modelos y preprocesadores; evita cargar `pickle` desde fuentes no confiables porque puede permitir ejecución de código |
| `mlflow` *(opcional)* | Tracking de experimentos y artefactos |

### Deployment / API
| Librería | Uso |
|---|---|
| `fastapi` | Construcción de API REST para inferencia |
| `uvicorn` | Servidor ASGI para FastAPI |
| `pydantic` | Validación del contrato de entrada/salida |

### RAG (Retrieval-Augmented Generation) — opcional/avanzado
| Librería | Uso |
|---|---|
| `langchain` / `llama-index` | Orquestación del flujo RAG |
| `faiss` / `chromadb` | Almacén de vectores para búsqueda semántica |
| `sentence-transformers` | Embeddings de texto |
| `openai` / `anthropic` | LLM para generación de respuestas |

---

## 3. Conceptos fundamentales a conocer

### Preprocesamiento y Feature Engineering
- Codificación cíclica de variables temporales (seno/coseno)
- One-hot encoding de variables categóricas
- Creación de lags y ventanas rolling (media, std, mediana)
- Transformaciones de estabilización de varianza (`log1p`)
- Escalado robusto (`RobustScaler`) ante outliers

### Manejo de datos faltantes
- Forward fill / backward fill en series temporales
- Interpolación temporal lineal
- `KNNImputer` para imputación basada en vecinos
- Flags de faltantes como features auxiliares

### Validación correcta en series temporales
- **Splits temporales** (por fecha, nunca random)
- **TimeSeriesSplit** (scikit-learn)
- **Walk-forward / rolling validation**
- Concepto de **data leakage** y cómo evitarlo

### Métricas de evaluación
- **MAE** (Mean Absolute Error)
- **RMSE** (Root Mean Squared Error)
- **MAPE / SMAPE** (cuidado con ceros)
- **R²** (coeficiente de determinación)
- Evaluación por segmentos (hora del día, estación, rango de PM2.5)

### Diagnóstico de modelos
- Análisis de residuales
- **ACF / PACF** (autocorrelación de residuales)
- Error vs nivel de PM2.5 (detección de fallos en picos)

### Explicabilidad de modelos
- Feature importance (árboles GBM)
- Permutation importance
- **SHAP values**

### MLOps ligero
- Estructura modular del proyecto (`data/`, `src/`, `notebooks/`, `docs/`)
- Versionado de artefactos (modelo + scaler + encoders)
- Monitoreo de data drift y performance drift

---

## 4. Conceptos de series temporales

- Estacionalidad (diaria, semanal, anual)
- Autocorrelación y correlación cruzada
- Diferenciación de series
- Pronóstico one-step-ahead vs multi-step
- Horizontes de predicción (h = 6h, 24h, etc.)
- Modelos recursivos vs directos para multi-step forecasting

---

## 5. Conocimientos de Python general
- Estructuración de proyectos (módulos, paquetes)
- `requirements.txt` / `pyproject.toml` para gestión de dependencias
- Uso de notebooks Jupyter para EDA y prototipos
- Git para control de versiones

---

## Resumen rápido de prioridades

| Prioridad | Herramienta / Concepto |
|---|---|
| 🔴 Esencial | `pandas`, `numpy`, `scikit-learn`, Ridge/Lasso, Random Forest, XGBoost/LightGBM |
| 🟠 Muy recomendable | `matplotlib`/`seaborn`, `missingno`, `statsmodels`, `shap`, TimeSeriesSplit, lags/rolling features |
| 🟡 Opcional / avanzado | `fastapi`, LSTM/GRU (PyTorch/Keras), `mlflow`, RAG (LangChain + vector DB) |
