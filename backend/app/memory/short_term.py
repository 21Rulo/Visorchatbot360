from app.models.database import get_db
import datetime

MAX_MENSAJES = 10

async def obtener_historial(session_id: str) -> list:
    db = get_db()
    if db is None:
        return []
    
    sesion = await db["sesiones_chat"].find_one({"session_id": session_id})
    if sesion and "mensajes" in sesion:
        return sesion["mensajes"]
    return []

async def agregar_mensaje(session_id: str, rol: str, contenido: str):
    db = get_db()
    if db is None:
        return

    nuevo_mensaje = {"role": rol, "content": contenido}
    
    await db["sesiones_chat"].update_one(
        {"session_id": session_id},
        {
            "$push": {
                "mensajes": {
                    "$each": [nuevo_mensaje],
                    "$slice": -MAX_MENSAJES # Mantiene solo los últimos N mensajes
                }
            },
            "$set": {"fecha_ultima_actividad": datetime.datetime.utcnow()}
        },
        upsert=True
    )

async def limpiar_sesion(session_id: str):
    db = get_db()
    if db is not None:
        await db["sesiones_chat"].delete_one({"session_id": session_id})