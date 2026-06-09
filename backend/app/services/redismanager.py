import os
import redis
import json
import numpy as np
import pandas as pd


class RedisManager:
    def __init__(self):
        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.ttl = {
            "pm25": 432000,
            "prediction": 25200
        }
        self.client = redis.from_url(self.redis_url, decode_responses=True)
        self.keys = {
            "pm25": "pm2-5:data",
            "prediction": "prediction:y_prediction"
        }
        self.columnas_prediction = [
            'date', 'pm2.5_(t+1)','pm2.5_(t+2)', 'pm2.5_(t+3)', 'pm2.5_(t+4)',
            'pm2.5_(t+5)', 'pm2.5_(t+6)', 'pm2.5_(t+7)'
        ]
        self.columnas_pm25 = ['date', 'pm2.5']


    def _normalizar_valor(self, v):
        if pd.isna(v):
            return None
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        if hasattr(v, "isoformat"):  # Timestamp
            return v.isoformat()
        return v

    def _validar_columnas(self, data: dict, columnas: list) -> dict:
        return {
            col: self._normalizar_valor(data.get(col))
            for col in columnas
        }

    def _to_timestamp(self, fecha_str: str) -> float:
        return pd.to_datetime(fecha_str).timestamp()

    def _guardar(self, capa: str, datos: dict, columnas: list):
        
        key = self.keys[capa]
        ttl = self.ttl[capa]

        # -------- Caso batch --------
        if isinstance(datos, list):
            mapping = {}

            for d in datos:
                datos_validados = self._validar_columnas(d, columnas)

                fecha = datos_validados.get("date")
                if not fecha:
                    raise ValueError("Campo 'date' es obligatorio")

                score = self._to_timestamp(fecha)

                payload = json.dumps(datos_validados)
                mapping[payload] = score

            if mapping:
                
                self.client.zadd(key, mapping)   # <-- 1 sola llamada
                self.client.expire(key, self.ttl)

            return

        # -------- Caso individual --------
        datos_validados = self._validar_columnas(datos, columnas)

        fecha = datos_validados.get("date")
        if not fecha:
            raise ValueError("Campo 'date' es obligatorio")

        score = self._to_timestamp(fecha)

        payload = json.dumps(datos_validados)

        self.client.zadd(key, {payload: score})
        self.client.expire(key, ttl)

    def _obtener_rango(self, capa: str, inicio: str, fin: str) -> pd.DataFrame:
        key = self.keys[capa]

        ts_inicio = self._to_timestamp(inicio)
        ts_fin = self._to_timestamp(fin)

        datos = self.client.zrangebyscore(key, ts_inicio, ts_fin)

        if not datos:
            return None

        return pd.DataFrame([json.loads(x) for x in datos])
    
    def _obtener_ultimo(self, capa: str) -> dict:
        """Obtiene el último registro guardado en una capa."""
        key = self.keys[capa]
        datos = self.client.zrange(key, -1, -1)
        
        if not datos:
            return None
        
        return json.loads(datos[0])


    def guardar_prediction(self, datos: dict):
        self._guardar("prediction", datos, self.columnas_prediction)

    def guardar_pm25(self, datos: dict):
        self._guardar("pm25", datos, self.columnas_pm25)


    def obtener_prediction(self, inicio: str = None, fin: str = None):
        if inicio is None or fin is None:
            result = self._obtener_ultimo("prediction")
            if result:
                return pd.DataFrame([result])
            return None
        return self._obtener_rango("prediction", inicio, fin)

    def obtener_pm25(self, inicio: str, fin: str):
        return self._obtener_rango("pm25", inicio, fin)


redismanager = RedisManager()






