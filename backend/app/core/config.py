from pathlib import Path
from dotenv import load_dotenv
import os
from groq import AsyncGroq  # <-- Importamos Groq aquí

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    MODELO_CHAT = "llama-3.3-70b-versatile"
    
    MONGO_URI = os.getenv("MONGO_URI")
    DATABASE_NAME = "visor360_db"

settings = Settings()

# --- NUEVO: Singleton para recursos compartidos ---
class SharedResources:
    _groq_client = None
    
    @classmethod
    def get_groq_client(cls) -> AsyncGroq:
        """Devuelve una única instancia del cliente Groq para toda la app"""
        if cls._groq_client is None:
            cls._groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        return cls._groq_client