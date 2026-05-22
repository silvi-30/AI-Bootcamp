"""
inference.py — Carga modelos XGBoost (h1..h6) y produce el pronóstico
de PM2.5 para las próximas 6 horas a partir de un timestamp del CSV de test.
Acomodando todo para el pronóstico de PM2.5.

El pipeline hace exactamente lo que quedo del preprocesamiento para la calibración:
  - Variables actuales (pm2.5, DEWP, TEMP, PRES, Iws, Is, Ir)
  - One-hot de cbwd y month
  - Lags t-1..t-7 de (pm2.5, DEWP, TEMP, PRES, Iws)
  → 58 features en total.
"""
from __future__ import annotations

from pathlib import Path
import joblib
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------------
ROOT = Path(__file__).parent
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"
TEST_CSV = DATA_DIR / "test_sample.csv"# Todo muy coquito, aca no... 
#estamos bajando data en tiempo real, puse a que cogiera a lo random

HORIZONS = list(range(1, 7))  # h1..h6
N_LAGS = 7
LAG_VARS = ["pm2.5", "DEWP", "TEMP", "PRES", "Iws"]


# ----------------------------------------------------------------------------
# Carga perezosa de artefactos (singleton)
# ----------------------------------------------------------------------------
class _Artifacts: # esta clase me la hizo claude, es para que no tenga que cargar los modelos cada vez
    """Carga única en memoria de scaler X, scalers Y, modelos y dataset."""

    def __init__(self) -> None:
        self.scaler_X = joblib.load(MODELS_DIR / "X_scaler.joblib")
        self.feature_cols: list[str] = list(self.scaler_X.feature_names_in_)
        self.scalers_y = {
            h: joblib.load(MODELS_DIR / f"y_h{h}_scaler.joblib") for h in HORIZONS
        }
        self.models = {
            h: joblib.load(MODELS_DIR / f"model_xgb_h{h}.joblib") for h in HORIZONS
        }
        self.df = self._load_test_df()

    @staticmethod # por eso hasta uso el decorator de static method
    def _load_test_df() -> pd.DataFrame:
        df = pd.read_csv(TEST_CSV, parse_dates=["datetime"])
        df = df.set_index("datetime").sort_index()
        return df


_artifacts: _Artifacts | None = None


def _get_artifacts() -> _Artifacts:
    global _artifacts
    if _artifacts is None:
        _artifacts = _Artifacts()
    return _artifacts


# ----------------------------------------------------------------------------
# Construcción del vector de features para un instante t
# ----------------------------------------------------------------------------
def _build_features_at(df: pd.DataFrame, t: pd.Timestamp) -> dict[str, float]:
    """Construye el diccionario de 58 features para predecir a partir de t.

    Requiere que existan al menos 7 horas previas a t en df.
    """
    if t not in df.index:
        raise ValueError(f"Timestamp {t} no está en el dataset.")
    idx = df.index.get_loc(t)
    if idx < N_LAGS:
        raise ValueError(f"No hay {N_LAGS} horas previas a {t}.")
    window = df.iloc[idx - N_LAGS: idx + 1]  # 8 filas: t-7..t

    current = window.iloc[-1]
    feat: dict[str, float] = {
        "pm2.5": float(current["pm2.5"]),
        "DEWP": float(current["DEWP"]),
        "TEMP": float(current["TEMP"]),
        "PRES": float(current["PRES"]),
        "Iws": float(current["Iws"]),
        "Is": float(current["Is"]),
        "Ir": float(current["Ir"]),
    }
    # One-hot cbwd
    for cv in ["NE", "NW", "SE", "cv"]:
        feat[f"cbwd_{cv}"] = 1 if current["cbwd"] == cv else 0
    # One-hot month (1..12)
    for mm in range(1, 13):
        feat[f"month_{mm}"] = 1 if current["month"] == mm else 0
    # Lags
    for var in LAG_VARS:
        for lag in range(1, N_LAGS + 1):
            feat[f"{var}_(t-{lag})"] = float(window.iloc[-1 - lag][var])
    return feat


# ----------------------------------------------------------------------------
# Ahora si, con lo que elabora el pronostico para entregar
# Yo puse que eligiera random la hora, para que cada vez que se accione
# nos de para mostrar ejemplos diferentes
# ----------------------------------------------------------------------------
def list_available_timestamps(min_hour_buffer: int = 7) -> pd.DatetimeIndex:
    """Timestamps válidos para predecir (con suficiente historial atrás)."""
    art = _get_artifacts()
    return art.df.index[min_hour_buffer:]


def predict_six_hours(t: pd.Timestamp) -> dict:
    """Pronostica PM2.5 para t+1h..t+6h dado un timestamp en el dataset.

    Devuelve:
      {
        "timestamp": pd.Timestamp,           # t
        "pm25_now": float,                   # PM2.5 actual en t
        "forecast": [(t+1, pred_1), ..., (t+6, pred_6)],  # lista de tuplas
        "meteo": {"TEMP": ..., "DEWP": ..., ...}          # condiciones actuales
      }
    """
    art = _get_artifacts()

    feat = _build_features_at(art.df, t)
    x_df = pd.DataFrame([[feat[c] for c in art.feature_cols]], columns=art.feature_cols)
    x_scaled = pd.DataFrame(
        art.scaler_X.transform(x_df), columns=art.feature_cols
    )

    forecast: list[tuple[pd.Timestamp, float]] = []
    for h in HORIZONS:
        model = art.models[h]
        sy = art.scalers_y[h]
        y_scaled = model.predict(x_scaled)
        y = sy.inverse_transform(y_scaled.reshape(-1, 1)).ravel()[0]
        # Recortar a 0 (no tiene sentido negativo)
        y = max(0.0, float(y))
        forecast.append((t + pd.Timedelta(hours=h), y))

    current = art.df.loc[t]
    return {
        "timestamp": t,
        "pm25_now": float(current["pm2.5"]),
        "forecast": forecast,
        "meteo": {
            "TEMP": float(current["TEMP"]),
            "DEWP": float(current["DEWP"]),
            "PRES": float(current["PRES"]),
            "Iws": float(current["Iws"]),
            "cbwd": str(current["cbwd"]),
        },
    }


def pick_random_timestamp(seed: int | None = None) -> pd.Timestamp:
    """Devuelve un timestamp aleatorio para demo (siempre dentro de 2014)."""
    rng = np.random.default_rng(seed)
    candidates = list_available_timestamps()
    # Filtrar solo 2014 para que sea claramente "test"
    candidates = candidates[candidates.year == 2014]
    return candidates[rng.integers(0, len(candidates))]
