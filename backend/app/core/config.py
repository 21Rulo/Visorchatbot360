from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent # Subimos un nivel más para llegar a la raíz
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    MODELO_CHAT = "llama-3.3-70b-versatile"
    
    # Nueva configuración para MongoDB
    MONGO_URI = os.getenv("MONGO_URI")
    DATABASE_NAME = "visor360_db"

settings = Settings()