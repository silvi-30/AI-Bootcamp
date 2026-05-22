"""
ClearAir — Streamlit MVP
Pronóstico de PM2.5 a 6 horas con asesor conversacional "Rocío".

Para correr:
    streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from inference import predict_six_hours, pick_random_timestamp
from advisor import (
    categorize,
    worst_of,
    chat_with_rocio,
)

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ClearAir — Pronóstico PM2.5",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
  /* Header oscuro */
  .clearair-header {
      background: linear-gradient(135deg, #162840 0%, #1f3a5c 100%);
      color: #ffffff;
      padding: 32px 36px;
      border-radius: 12px;
      font-family: 'Helvetica Neue', 'Helvetica', Arial, sans-serif;
      box-shadow: 0 4px 14px rgba(22, 40, 64, 0.18);
      margin-bottom: 28px;
  }
  .clearair-header .header-content {
      display: flex;
      flex-direction: column;
      gap: 6px;
  }
  .clearair-header .brand-row {
      display: flex;
      align-items: center;
      gap: 14px;
  }
  .clearair-header .brand-icon {
      font-size: 38px;
      line-height: 1;
  }
  .clearair-header .brand {
      font-weight: 700;
      font-size: 38px;
      letter-spacing: -0.5px;
      line-height: 1;
  }
  .clearair-header .brand-tagline {
      font-size: 15px;
      font-weight: 400;
      opacity: 0.75;
      letter-spacing: 0.3px;
      margin-left: 52px;
  }

  /* Banner de calidad del aire */
  .quality-banner {
      border-radius: 8px;
      padding: 16px 18px;
      margin: 22px 0 26px 0;
      display: flex;
      align-items: flex-start;
      gap: 14px;
  }
  .quality-dot {
      width: 36px; height: 36px;
      border-radius: 50%;
      flex-shrink: 0;
      margin-top: 2px;
  }
  .quality-text { flex: 1; }
  .quality-title {
      font-weight: 700;
      font-size: 18px;
      margin-bottom: 4px;
      line-height: 1.2;
  }
  .quality-detail {
      font-size: 14px;
      line-height: 1.45;
      opacity: 0.92;
  }

  /* Tarjetas horarias mejoradas */
  .hour-card {
      border: none;
      border-radius: 10px;
      padding: 14px 8px 14px 8px;
      text-align: center;
      background: #ffffff;
      height: 100%;
      box-shadow: 0 2px 8px rgba(22, 40, 64, 0.08);
      border-top: 4px solid var(--card-color, #d6dde3);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .hour-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 14px rgba(22, 40, 64, 0.12);
  }
  .hour-card .hour-label {
      color: #8a99a8;
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 4px;
  }
  .hour-card .hour-value {
      font-size: 32px;
      font-weight: 700;
      line-height: 1.1;
      font-family: 'Helvetica Neue', Arial, sans-serif;
  }
  .hour-card .hour-unit {
      font-size: 11px;
      color: #8a99a8;
      margin-top: 2px;
  }

  /* Rocío - card */
  .rocio-card {
      background: linear-gradient(135deg, #f0f9f3 0%, #e3f6ec 100%);
      border-left: 5px solid #1f9d6a;
      border-radius: 10px;
      padding: 18px 22px;
      margin: 32px 0 18px 0;
      display: flex;
      align-items: center;
      gap: 16px;
      box-shadow: 0 2px 8px rgba(31, 157, 106, 0.08);
  }
  .rocio-avatar {
      width: 52px; height: 52px;
      border-radius: 50%;
      background: #ffffff;
      border: 2px solid #1f9d6a;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      flex-shrink: 0;
      box-shadow: 0 2px 6px rgba(31, 157, 106, 0.15);
  }
  .rocio-text { flex: 1; }
  .rocio-name {
      font-size: 18px;
      font-weight: 700;
      color: #0f6a45;
      line-height: 1.2;
      margin-bottom: 2px;
  }
  .rocio-role {
      font-size: 13.5px;
      color: #4a7a5f;
      line-height: 1.35;
  }

  /* Preguntas sugeridas — pill style */
  .stButton > button[kind="secondary"] {
      border-radius: 20px !important;
      border: 1.5px solid #b8d4c5 !important;
      background: #f8fcf9 !important;
      color: #0f6a45 !important;
      font-size: 13px !important;
      transition: all 0.15s ease !important;
  }
  .stButton > button[kind="secondary"]:hover {
      border-color: #1f9d6a !important;
      background: #e3f6ec !important;
      transform: translateY(-1px);
  }

  /* Chat input — respeta el ancho del contenido */
  div[data-testid="stChatInput"] {
      max-width: 1100px;
      margin-left: auto;
      margin-right: auto;
  }

  /* Footer */
  .clearair-footer {
      text-align: center;
      color: #8a99a8;
      font-size: 12px;
      padding: 24px 0 12px 0;
      margin-top: 36px;
      border-top: 1px solid #e4e8ec;
      line-height: 1.6;
  }

  /* Reducir el padding default de Streamlit */
  .block-container { padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1100px; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="clearair-header">
        <div class="header-content">
            <div class="brand-row">
                <span class="brand-icon">🌫️</span>
                <span class="brand">ClearAir</span>
            </div>
            <div class="brand-tagline">Pronóstico de calidad del aire · PM2.5</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Estado de sesión
# ---------------------------------------------------------------------------
if "prediction" not in st.session_state:
    st.session_state.prediction = None
if "messages" not in st.session_state:
    st.session_state.messages = []  # historia del chat con Rocío

# ---------------------------------------------------------------------------
# Selector de ciudad + botón consultar
# ---------------------------------------------------------------------------
st.markdown("**Ciudad**")
col_city, col_btn = st.columns([4, 1])
with col_city:
    city = st.selectbox(
        label="Ciudad",
        options=["Beijing, China"],
        index=0,
        label_visibility="collapsed",
        help="Por ahora solo disponible Beijing — más ciudades en camino.",
    )
with col_btn:
    consult = st.button("Consultar", type="primary", use_container_width=True)

# Disparar pronóstico
if consult:
    t = pick_random_timestamp()
    st.session_state.prediction = predict_six_hours(t)
    # Resetear el chat al pedir un pronóstico nuevo
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# Si no hay pronóstico todavía, mostrar mensaje inicial
# ---------------------------------------------------------------------------
if st.session_state.prediction is None:
    st.info(
        "👆 Selecciona una ciudad y pulsa **Consultar** para ver el pronóstico de "
        "PM2.5 de las próximas 6 horas. Esta demo usa datos de testeo reales del "
        "modelo XGBoost entrenado sobre Beijing (2010–2014)."
    )
    st.stop()

pred = st.session_state.prediction

# ---------------------------------------------------------------------------
# Banner de calidad (basado en el peor valor del pronóstico)
# ---------------------------------------------------------------------------
forecast_values = [v for _, v in pred["forecast"]]
worst_level = worst_of(forecast_values)
peak_value = max(forecast_values)

st.markdown(
    f"""
    <div class="quality-banner"
         style="background:{worst_level.bg}; border-left:6px solid {worst_level.color};">
        <div class="quality-dot" style="background:{worst_level.color};"></div>
        <div class="quality-text" style="color:{worst_level.text};">
            <div class="quality-title">{worst_level.label}</div>
            <div class="quality-detail">
                PM2.5 estimado pico: <b>{peak_value:.0f} µg/m³</b> · {worst_level.advice}
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 6 tarjetas (+1h ... +6h)
# ---------------------------------------------------------------------------
cols = st.columns(6, gap="small")
for i, (ts, val) in enumerate(pred["forecast"]):
    level = categorize(val)
    with cols[i]:
        st.markdown(
            f"""
            <div class="hour-card" style="--card-color:{level.color};">
                <div class="hour-label">+{i + 1}h</div>
                <div class="hour-value" style="color:{level.number_color};">
                    {val:.0f}
                </div>
                <div class="hour-unit">µg/m³</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Caption pequeño con el timestamp del ejemplo
st.caption(
    f"Pronóstico generado a partir del estado del aire en "
    f"**{pred['timestamp'].strftime('%Y-%m-%d %H:%M')}** "
    f"(muestra del conjunto de test 2014). "
    f"Temperatura: {pred['meteo']['TEMP']:.1f} °C · "
    f"Viento: {pred['meteo']['cbwd']} · "
    f"PM2.5 actual: {pred['pm25_now']:.0f} µg/m³"
)

# ---------------------------------------------------------------------------
# Chat con Rocío
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="rocio-card">
        <div class="rocio-avatar">🌿</div>
        <div class="rocio-text">
            <div class="rocio-name">Habla con Rocío</div>
            <div class="rocio-role">
                Tu asesora de calidad del aire — te ayuda a interpretar el pronóstico
                y a tomar decisiones según tu salud y tus planes.
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sugerencias de preguntas guiadas (chips)
SUGGESTIONS = [
    "¿Puedo salir a correr ahora?",
    "Tengo asma, ¿qué precauciones tomar?",
    "¿Es seguro abrir las ventanas?",
    "¿Qué hora es la mejor para salir?",
]
st.markdown("**Preguntas sugeridas:**")
chip_cols = st.columns(len(SUGGESTIONS))
clicked_suggestion: str | None = None
for chip_col, suggestion in zip(chip_cols, SUGGESTIONS):
    with chip_col:
        if st.button(suggestion, key=f"chip_{suggestion}", use_container_width=True):
            clicked_suggestion = suggestion

# Mostrar historial del chat
for msg in st.session_state.messages:
    avatar = "🌿" if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Input de usuario: chip clickeado o text input
user_input = clicked_suggestion or st.chat_input("Pregúntale algo a Rocío...")

if user_input:
    # Mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generar respuesta de Rocío
    with st.chat_message("assistant", avatar="🌿"):
        with st.spinner("Rocío está pensando..."):
            try:
                reply = chat_with_rocio(
                    user_message=user_input,
                    history=st.session_state.messages[:-1],
                    prediction=pred,
                )
            except Exception as e:
                reply = f"😅 Ups, tuve un problema: `{e}`. Intenta de nuevo."
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="clearair-footer">
        ClearAir · Demo MVP · Modelo XGBoost entrenado sobre Beijing 2010–2014<br>
        Umbrales basados en WHO Global Air Quality Guidelines 2021
    </div>
    """,
    unsafe_allow_html=True,
)
