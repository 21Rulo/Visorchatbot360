from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path)

class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    MODELO_CHAT = "llama-3.3-70b-versatile"

settings = Settings()

print("API KEY cargada:", settings.GROQ_API_KEY)