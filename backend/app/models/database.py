from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db_client = MongoDB()

async def connect_to_mongo():
    """Crea la conexión al iniciar la API"""
    db_client.client = AsyncIOMotorClient(settings.MONGO_URI)
    db_client.db = db_client.client[settings.DATABASE_NAME]
    print("✅ Conexión a MongoDB Atlas establecida")

async def close_mongo_connection():
    """Cierra la conexión al apagar la API"""
    if db_client.client:
        db_client.client.close()
        print("❌ Conexión a MongoDB Atlas cerrada")

def get_db():
    """Función de utilidad para obtener la base de datos"""
    return db_client.db