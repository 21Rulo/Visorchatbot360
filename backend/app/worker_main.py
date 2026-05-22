import time
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.logger import logger

# Importamos tus scripts actuales
from app.scripts.ingesta import procesar_jsons_a_chroma
from app.data_ingestion.pdf_processor import DataIngestor
from app.data_ingestion.web_scraper import WebIngestor
from app.scripts.limpieza_memoria import limpiar_checkpoints_huerfanos

def tarea_mantenimiento_semanal():
    logger.info("🚜 Iniciando mantenimiento automatizado...")
    try:
        # 1. Limpiar memoria/vectores si es necesario
        limpiar_checkpoints_huerfanos()
        
        # 2. Ingesta de JSONs base
        logger.info("Procesando JSONs...")
        procesar_jsons_a_chroma()
        
        # 3. Ingesta de PDFs
        logger.info("Procesando PDFs...")
        pdf_ingestor = DataIngestor()
        pdf_ingestor.process_all_pdfs()
        
        # 4. Ingesta de Web Scraping
        logger.info("Procesando Web Scraping...")
        web_ingestor = WebIngestor()
        web_ingestor.procesar_desde_archivo()
        
        logger.success("🚜 Mantenimiento semanal completado con éxito.")
    except Exception as e:
        logger.error(f"❌ Error durante el mantenimiento: {e}")

if __name__ == "__main__":
    logger.info("🤖 Worker automatizado inicializado.")
    
    scheduler = BackgroundScheduler()
    
    # Programamos la tarea para que corra todos los domingos a las 3:00 AM
    scheduler.add_job(tarea_mantenimiento_semanal, 'cron', day_of_week='sun', hour=3, minute=0)
    
    # TIP PARA PRUEBAS: Descomenta la siguiente línea para que corra cada 5 minutos
    #scheduler.add_job(tarea_mantenimiento_semanal, 'interval', minutes=10)
    
    scheduler.start()
    
    try:
        # Mantenemos el contenedor vivo (reemplaza al tail -f /dev/null)
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()