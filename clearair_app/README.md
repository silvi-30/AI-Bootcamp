# ClearAir — Streamlit MVP

Pronóstico de PM2.5 a 6 horas para Beijing con asesor conversacional **Rocío**... me pareció super tierni el nombreee, igual se lo podemos cambiar después.

Usa los modelos XGBoost `h1..h6` entrenados sobre el dataset *Beijing PM2.5*
(2010–2014) y los muestra en una interfaz tipo dashboard con sistema de
semáforo (verde / naranja / rojo / morado) según las guías de la OMS para PM2.5.
Por ahora seleccioné los de la OMS, pero por ejemplo Beijing tiene su propio esquema y la EPA (la agencia medioambiental de USA) tiene otros. Podríamos también implementar después como mejora que el usuario seleccione que umbrales prefiere. 

---

## Estructura

```
clearair_app/
├── app.py                  # Streamlit principal (UI + flujo)
├── inference.py            # Carga modelos + scalers, construye features, predice
├── advisor.py              # Categorización OMS + chat con Claude (Rocío)
├── requirements.txt
├── .env.example            # Plantilla para tu API key (renombra a .env)
├── data/
│   └── test_sample.csv     # Muestra del CSV imputado (2013-12-25 → 2014-12-31)
└── models/
    ├── X_scaler.joblib
    ├── y_h1_scaler.joblib  ...  y_h7_scaler.joblib
    └── model_xgb_h1.joblib ...  model_xgb_h6.joblib
```

---

## Cómo correrlo localmente

```bash
# 1. (recomendado) entorno virtual
python -m venv .venv
source .venv/bin/activate         # en Windows: .venv\Scripts\activate

# 2. instalar dependencias
pip install -r requirements.txt

# 3. (opcional, para chat real) configurar API key de Anthropic
cp .env.example .env
# luego abre .env y pega tu key real de console.anthropic.com

# 4. correr la app
streamlit run app.py
```

La app abre en `http://localhost:8501`.

---

## Cómo funciona

1. **Selección de ciudad** — por ahora solo Beijing está disponible (mockup).
2. **Botón "Consultar"** — escoge un timestamp aleatorio dentro de 2014 (el
   conjunto de test del modelo), construye las 58 features que el XGBoost
   espera (variables actuales + lags t-1..t-7 + one-hots de cbwd y month),
   escala con `X_scaler` y predice con los 6 modelos `h1..h6`. Cada salida se
   des-escala con su `y_scaler` correspondiente.
3. **Banner de calidad** — color y mensaje basados en el **peor valor** del
   pronóstico, usando los **umbrales OMS 2021** (ver sección dedicada abajo).
4. **6 tarjetas** — una por horizonte (+1h ... +6h), con el valor numérico
   coloreado según su propia categoría.
5. **Chat con Rocío** — en la parte final de la interfaz. Por ahora responde 
   con mensajes locales según  el nivel pronosticado.

---

## Umbrales de alerta

Usamos los **WHO Global Air Quality Guidelines 2021** (publicadas en
septiembre de 2021), que son la referencia más rigurosa y actualizada a nivel
mundial para PM2.5.

La OMS define 5 niveles para el promedio de PM2.5 en 24 horas:

| Nivel OMS | µg/m³ | Significado |
|---|---|---|
| AQG (Air Quality Guideline) | 15 | Guía recomendada |
| Interim Target 4 | 25 | |
| Interim Target 3 | 37.5 | |
| Interim Target 2 | 50 | |
| Interim Target 1 | 75 | Objetivo mínimo para países muy contaminados |

Para el MVP simplificamos a **4 categorías** agrupando estos cortes en tramos
clínicamente significativos:

| Categoría | Corte (µg/m³) | Color | Anclaje OMS |
|---|---|---|---|
| **Bueno** | < 15 | 🟢 verde | Bajo la guía AQG |
| **Moderado** | < 35 | 🟠 naranja | Entre IT-4 e IT-3 |
| **Poco saludable** | < 75 | 🔴 rojo | Entre IT-3 e IT-1 |
| **Peligroso** | ≥ 75 | 🟣 morado | Sobre el peor Interim Target |

### Nota metodológica [DISCLAIMER!]

Los umbrales OMS están definidos sobre **promedios de 24 horas**, no sobre
valores horarios. Nuestro modelo predice valores horarios, así que estos
cortes son una **aproximación operativa**, no un diagnóstico clínico. 

---

## Notas importantes

- **El pronóstico no es "en vivo"**: los datos meteorológicos no llegan en
  tiempo real desde una API externa. Para cada consulta se elige un punto
  aleatorio del conjunto de test (2014). Esto es intencional: queremos mostrar
  el modelo funcionando con datos reales que sí vio el entrenamiento como
  test, sin necesidad de montar un pipeline de ingesta de datos.

- **Modelos**: se entrenaron en el notebook `train_xgboost_final.ipynb`.
  Los `joblib` ya incluyen el `best_iteration` definido por early stopping.

---

## Roadmap (lo que sigue)

- [ ] Agregar más ciudades (requiere modelo entrenado por ciudad o un único
  modelo con feature de ubicación).
- [ ] Reemplazar el `pick_random_timestamp` por ingesta real desde la API
  meteorológica que consideramos para pronóstico en tiempo real.
- [ ] Mostrar un gráfico de tendencia (línea con +1h..+6h) además de las
  tarjetas.
- [ ] Permitir que Rocío recuerde condiciones de salud del usuario entre
  sesiones (memoria persistente)... básicamente entrenar todo el RAG
