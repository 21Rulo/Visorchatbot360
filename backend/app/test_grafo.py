import asyncio
import uuid
from app.agents.agente_control import app_chatbot
from app.models.database import connect_to_mongo, close_mongo_connection

async def probar_chatbot():
    # 1. Iniciamos conexión a Mongo
    await connect_to_mongo()
    
    # 2. Simulamos una sesión
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}
    
    print(f"\n--- INICIANDO SESIÓN: {session_id} ---")
    
    # Interacción 1
    inputs = {
        "mensaje": "Hola, ¿qué es ESIT?",
        "contexto_ubicacion": "Entrada Principal",
        "session_id": session_id
    }
    print(f"Usuario: {inputs['mensaje']}")
    resultado = await app_chatbot.ainvoke(inputs, config=config)
    print(f"IA (Intención {resultado['intencion']}): {resultado['respuesta']}\n")
    
    # Interacción 2 (Para probar que recuerda)
    inputs = {
        "mensaje": "¿Y cuáles son sus carreras?",
        "contexto_ubicacion": "Entrada Principal",
        "session_id": session_id
    }
    print(f"Usuario: {inputs['mensaje']}")
    resultado = await app_chatbot.ainvoke(inputs, config=config)
    print(f"IA: {resultado['respuesta']}\n")
    
    print("Revisa tu base de datos MongoDB. Deberías ver las nuevas colecciones de LangGraph.")
    
    # 3. Cerramos conexión
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(probar_chatbot())