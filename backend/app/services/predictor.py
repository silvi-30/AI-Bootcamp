import joblib
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

BASE_PATH = Path(__file__).parent.parent.parent

class DataProcessor:
    def __init__(self):# Hora de lugar
        self.zona = "America/Bogota" # Remplazar por  la zona horaria
        self.date = datetime.now(ZoneInfo(self.zona)).replace(minute=0, second=0, microsecond=0)  # Redondear a la hora más cercana
        self.dummies_path = BASE_PATH / "app" / "data" / "dummies" / "dummies_2026.csv"
        self.ingest_data_path = BASE_PATH / "app" / "data" / "ingest" / "ingest_data.csv"
        self.columnas_ingest = ['DEWP', 'TEMP', 'PRES', 'cbwd', 'Iws', 'Is', 'Ir', 'pm2.5'] 
        self.columnas_inferencia = [
            'pm2.5', 'DEWP', 'TEMP', 'PRES', 'Iws', 'Is', 'Ir', 'cbwd_NE', 'cbwd_NW',
            'cbwd_SE', 'cbwd_cv', 'month_1', 'month_2', 'month_3', 'month_4', 'month_5',
            'month_6', 'month_7', 'month_8', 'month_9', 'month_10', 'month_11', 'month_12',
            'pm2.5_(t-1)', 'pm2.5_(t-2)', 'pm2.5_(t-3)', 'pm2.5_(t-4)', 'pm2.5_(t-5)',
            'pm2.5_(t-6)', 'pm2.5_(t-7)', 'DEWP_(t-1)', 'DEWP_(t-2)', 'DEWP_(t-3)',
            'DEWP_(t-4)', 'DEWP_(t-5)', 'DEWP_(t-6)', 'DEWP_(t-7)', 'TEMP_(t-1)',
            'TEMP_(t-2)', 'TEMP_(t-3)', 'TEMP_(t-4)', 'TEMP_(t-5)', 'TEMP_(t-6)',
            'TEMP_(t-7)', 'PRES_(t-1)', 'PRES_(t-2)', 'PRES_(t-3)', 'PRES_(t-4)',
            'PRES_(t-5)', 'PRES_(t-6)', 'PRES_(t-7)', 'Iws_(t-1)', 'Iws_(t-2)',
            'Iws_(t-3)', 'Iws_(t-4)', 'Iws_(t-5)', 'Iws_(t-6)', 'Iws_(t-7)'
        ]

    def get_last_date(self):
        try:
            df = pd.read_csv(self.ingest_data_path)
            df["date"] = pd.to_datetime(df["date"])
            if df["date"].dt.tz is None:
                df["date"] = df["date"].dt.tz_localize(self.zona)
            return df["date"].max()
        except FileNotFoundError:
            return None

    def get_date_range(self):
        t_now = self.date
        t_last = self.get_last_date()
        if t_last is None:
            start = datetime(2026, 1, 1, tzinfo=ZoneInfo(self.zona))
        else:
            start = t_last + pd.Timedelta(hours=1)
        start = pd.Timestamp(start).tz_convert(self.zona)
        end = pd.Timestamp(t_now).tz_convert(self.zona)
        return start, end


    def simulation_download_data(self, var): 
    # simula a descarga de datos
    # en este caso es solo un filtro de un csv, pero podría ser una consulta a una API
    # o cualquier otra fuente de datos, incluso diferentes para cada variable

        start, end = self.get_date_range()
        df_source = pd.read_csv(self.dummies_path)
        df_source["date"] = pd.to_datetime(
            df_source[["year", "month", "day", "hour"]]
        ).dt.tz_localize(self.zona)
        df = df_source[
            (df_source["date"] >= start) & (df_source["date"] <= end)
        ][["date", var]]

        return df


    def ingest_data_dummy(self):

        start, end = self.get_date_range()
        if start > end:
            print("\nNo hay datos nuevos para ingerir.")
            return
        df_ingest = pd.DataFrame({"date": pd.date_range(start=start, end=end, freq="h")})

        # columnas derivadas de date 
        df_ingest["year"] = df_ingest["date"].dt.year
        df_ingest["month"] = df_ingest["date"].dt.month
        df_ingest["day"] = df_ingest["date"].dt.day
        df_ingest["hour"] = df_ingest["date"].dt.hour

        for var in self.columnas_ingest:
            df_var = self.simulation_download_data(var)
            df_ingest = df_ingest.merge(df_var, on="date", how="left")

        df_ingest["date"] = df_ingest["date"].dt.tz_localize(None)  # Eliminar la zona horaria para guardar en CSV
        try:
            df_existing = pd.read_csv(self.ingest_data_path)
            df_existing["date"] = pd.to_datetime(df_existing["date"])
            df_final = pd.concat([df_existing, df_ingest])
        except FileNotFoundError:
            df_final = df_ingest

        df_final = df_final.sort_values("date").drop_duplicates("date")
        df_final.to_csv(self.ingest_data_path, index=False)

        print(f"\nDatos ingeridos desde {start} hasta {end}. Total filas: {len(df_ingest)}")


    def features_for_inferece(self):
        
        df = pd.read_csv(self.ingest_data_path, parse_dates=["date"])

        if df.empty:
            print("No hay datos para inferencia.")
            return None

        df = df.sort_values("date")
        df = df.drop_duplicates(subset="date", keep="last")
        df = df.set_index("date").asfreq("h")

        # One-hot encoding para cbwd y month
        df = pd.get_dummies(df, columns=["cbwd"],  prefix="", prefix_sep="cbwd_",  dtype=int)
        df = pd.get_dummies(df, columns=["month"], prefix="", prefix_sep="month_", dtype=int)
        
        # Eliminamos componentes de fecha 
        df = df.drop(columns=["year", "day", "hour"], errors="ignore")
        
        # Agregamos lags para las variables numéricas (pm2.5, DEWP, TEMP, PRES, Iws)
        N_LAGS = 7
        variables_lag = ["pm2.5", "DEWP", "TEMP", "PRES", "Iws"]

        for variable in variables_lag:
            for i in range(1, N_LAGS + 1):
                df[f"{variable}_(t-{i})"] = df[variable].shift(i)

        dummy_columns = [
            c for c in self.columnas_inferencia
            if c.startswith("cbwd_") or c.startswith("month_")
        ]

        for col in dummy_columns:
            if col not in df.columns:
                df[col] = 0
        
        # Restaurar date como columna
        df = df.reset_index()
        date = df["date"].iloc[-1]

        # ordenar columnas exactamente como el modelo espera
        df = df.reindex(columns=self.columnas_inferencia)

        # devolver SOLO la última fila (estado actual)
        X = df.iloc[[-1]].copy()

        return date, X
        


class Predictor:
    def __init__(self):
            self.X_scaler = joblib.load(BASE_PATH / "app" / "models" / "X_scaler.joblib")
            self.modelos = {}
            self.y_scalers = {}
            
            for h in range(1, 8):
                self.modelos[h] = joblib.load(BASE_PATH / "app" / "models" / f"model_xgb_h{h}.joblib")
                self.y_scalers[h] = joblib.load(BASE_PATH / "app" / "models" / f"y_h{h}_scaler.joblib")

    def predict_pm25(self, date, X):
        """
        Realiza predicciones de PM2.5 para 7 horizontes temporales.
        
        Args:
            X (pd.DataFrame): Features ya procesadas con columnas en orden correcto.
        
        Returns:
            dict: Pronósticos desescalados por horizonte {'h1': valor, 'h2': valor, ..., 'h7': valor}
        """
        X_scaled = self.X_scaler.transform(X)
        predictions = {}
        
        for h in range(1, 8):
            modelo = self.modelos[h]
            scaler_y = self.y_scalers[h]
            
            pred_scaled = modelo.predict(X_scaled)
            pred_desescalado = scaler_y.inverse_transform(pred_scaled.reshape(-1, 1))[0, 0]

            fecha_pronostico = date + timedelta(hours=h)
            predictions[f'h{h}'] = {
                'fecha': fecha_pronostico.strftime('%Y-%m-%d %H:%M'),
                'pm25': round(float(pred_desescalado), 2)
            }
        
        return predictions





dataprocessor = DataProcessor()
predictor = Predictor()
    
"""

class Predictor:
    def __init__(self):
        self.X_scaler = joblib.load(BASE_PATH / "X_scaler.joblib")
        self.modelos = {}
        self.y_scalers = {}
        
        for h in range(1, 8):
            self.modelos[h] = joblib.load(BASE_PATH / f"model_xgb_h{h}.joblib")
            self.y_scalers[h] = joblib.load(BASE_PATH / f"y_h{h}_scaler.joblib")
    
    def predecir(self, datos, horizonte: int):
        datos_escalados = self.X_scaler.transform(datos)
        prediccion = self.modelos[horizonte].predict(datos_escalados)
        prediccion_original = self.y_scalers[horizonte].inverse_transform(prediccion.reshape(-1, 1))
        return prediccion_original[0][0]

predictor = Predictor()
"""