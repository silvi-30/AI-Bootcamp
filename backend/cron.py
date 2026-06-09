import argparse
from dotenv import load_dotenv
load_dotenv()
import os
from datetime import datetime
import pandas as pd
from app.services.predictor import dataprocessor, predictor
from app.services.redismanager import redismanager

"""
Módulo CRON - Ingesta, Inferencia y Predicción Automática de PM2.5

Este módulo ejecuta automáticamente el pipeline completo cada hora:

1. INGESTA DE DATOS: Descarga datos meteorológicos desde fuentes externas
   (simulado con CSV dummy en desarrollo)

2. PREPARACIÓN DE FEATURES: Procesa y escala datos para el modelo ML
   - One-hot encoding de variables categóricas
   - Lags temporales (7 horizontes)
   - Normalización con scalers entrenados

3. PREDICCIÓN: Genera pronósticos de PM2.5 para 7 horizontes (h+1 a h+7)
   - Utiliza 7 modelos XGBoost independientes
   - Desescala resultados a unidades originales (µg/m³)

4. ALMACENAMIENTO: Guarda pronósticos en Redis
   - Clave: "prediction:y_prediction"
   - TTL: 7 horas
   - Formato: Sorted Set ordenado por timestamp

FLUJO:
   dataprocessor.ingest_data_dummy() 
   → dataprocessor.features_for_inferece()
   → predictor.predict_pm25(date, df)
   → redismanager.guardar_prediction(datos)

USO:
   python cron.py              # Ejecutar pipeline
   python cron.py --run        # Ejecutar pipeline explicitamente
   python cron.py --help       # Ver este mensaje

   
O desde scheduler (APScheduler, Celery, etc):
   from cron import run
   scheduler.add_job(run, 'cron', hour='*')  # Cada hora
"""


def run():

    print("------------------------------------------------------------------------------")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Iniciando proceso de ingesta, inferencia y predicción...")
    
    try:
        # 1. INGESTA
        dataprocessor.ingest_data_dummy()
        
        # 2. PREPARACIÓN DE FEATURES
        date, df = dataprocessor.features_for_inferece()
        print(f"\nFecha de inferencia: {date}")   
        
        # 3. PREDICCIÓN
        prediction = predictor.predict_pm25(date, df)
        print("\nPredicción:")
        for h, data in prediction.items():
            print(f"{h}: {data['fecha']} -> {data['pm25']} µg/m³")
        
        # 4. ALMACENAMIENTO EN REDIS
        datos_redis = {
            'date': date,
            **{f'pm2.5_(t+{h})': prediction[f'h{h}']['pm25'] for h in range(1, 8)}
        }
        redismanager.guardar_prediction(datos_redis)
        print("\nDatos guardados en Redis ✓")
        
        print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Proceso completado exitosamente ✓")
        
    except Exception as e:
        print(f"\n✗ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("------------------------------------------------------------------------------")

def main():
    """Punto de entrada principal con argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Pipeline automático de ingesta, inferencia y predicción de PM2.5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--run',
        action='store_true',
        help='Ejecutar el pipeline completo'
    )
    
    args = parser.parse_args()
    
    if args.run or not args.__dict__.get('run'):
        run()

if __name__ == "__main__":
    main()