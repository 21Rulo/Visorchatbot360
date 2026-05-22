import sys
import os
from loguru import logger
from app.core.config import settings

# Configuramos Loguru para que formatee bonito en consola (útil para `docker compose logs`)
logger.remove() # Quitamos el logger por defecto
entorno = os.getenv("ENTORNO", "desarrollo")
if entorno == "produccion":
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG"
    )

from pathlib import Path
ruta_logs = Path("logs")
ruta_logs.mkdir(exist_ok=True)

logger.add(
    "logs/visor360_{time}.log", 
    rotation="10 MB",     # Crea un archivo nuevo cuando llegue a 10MB
    retention="10 days",  # Borra los archivos más viejos de 10 días
    level="INFO",         # En producción filtramos lo más ruidoso (dejamos INFO, WARNING, ERROR, SUCCESS)
    enqueue=True          # Muy importante para FastAPI: asegura que la escritura sea segura con concurrencia asíncrona
)