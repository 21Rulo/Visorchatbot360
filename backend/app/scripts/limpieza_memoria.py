import os
import sys
from pymongo import MongoClient

# Ajustar el path para poder importar módulos de la app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def limpiar_checkpoints_huerfanos():
    print("🧹 Iniciando limpieza de memoria de LangGraph...")
    
    try:
        # Usamos PyMongo síncrono para esta tarea de mantenimiento
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.DATABASE_NAME]
        
        # 1. Obtener todas las sesiones activas (las que el TTL aún no ha borrado)
        # Usamos distinct() para obtener una lista plana de los IDs
        sesiones_activas = db["sesiones_chat"].distinct("session_id")
        print(f"📌 Sesiones activas válidas: {len(sesiones_activas)}")
        
        # Si no hay sesiones activas, la lista estará vacía, y el $nin borrará TODO.
        # Esto es un comportamiento correcto si realmente no hay nadie conectado.
        
        # 2. Limpiar la colección 'checkpoints'
        res_checkpoints = db["checkpoints"].delete_many({
            "thread_id": {"$nin": sesiones_activas}
        })
        print(f"🗑️ Memorias base eliminadas: {res_checkpoints.deleted_count}")
        
        # 3. Limpiar la colección 'checkpoint_writes' (donde LangGraph guarda pasos intermedios)
        res_writes = db["checkpoint_writes"].delete_many({
            "thread_id": {"$nin": sesiones_activas}
        })
        print(f"🗑️ Pasos intermedios eliminados: {res_writes.deleted_count}")
        
        print("✅ Mantenimiento de base de datos completado con éxito.")
        
    except Exception as e:
        print(f"❌ Error durante la limpieza: {e}")
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    limpiar_checkpoints_huerfanos()