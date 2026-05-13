from datetime import datetime, timezone
from langgraph.graph import StateGraph, END
from app.models.schemas import AgentState
from app.core.config import settings, SharedResources
from app.agents.agente_guia import nodo_guia
from app.agents.agente_info import nodo_info
from app.memory.checkpointer import memory_saver
from app.models.database import get_db

# --- NODO CLASIFICADOR ---
async def nodo_clasificador(state: AgentState) -> dict:
    """
    Analiza el mensaje para decidir a qué agente enviarlo.
    """
    client = SharedResources.get_groq_client()
    
    system_prompt = """
    Eres el Orquestador del Chatbot del IPN. Clasifica la intención del usuario.
    Responde ÚNICAMENTE con UNA palabra:
    - GUIA: Saludos, conversación general o sobre el recorrido virtual.
    - INFO: Dudas sobre carreras, trámites, becas o info institucional.
    """

    try:
        response = await client.chat.completions.create(
            model=settings.MODELO_CHAT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": state["mensaje"]}
            ],
            temperature=0.0,
            max_tokens=10
        )
        intencion = response.choices[0].message.content.strip().upper()
    except Exception:
        intencion = "GUIA" # Fallback seguro

    return {"intencion": intencion}

# --- LÓGICA DE ENRUTAMIENTO (Router) ---
def enrutador_de_intencion(state: AgentState):
    """
    Función que decide el siguiente paso en el grafo.
    """
    if "INFO" in state["intencion"]:
        return "agente_info"
    return "agente_guia"

# --- DEFINICIÓN DEL GRAFO ---
workflow = StateGraph(AgentState)

# 1. Agregar los Nodos
workflow.add_node("clasificador", nodo_clasificador)
workflow.add_node("agente_guia", nodo_guia)
workflow.add_node("agente_info", nodo_info)

# 2. Configurar el Flujo (Aristas)
workflow.set_entry_point("clasificador")

workflow.add_conditional_edges(
    "clasificador",
    enrutador_de_intencion,
    {
        "agente_info": "agente_info",
        "agente_guia": "agente_guia"
    }
)

workflow.add_edge("agente_guia", END)
workflow.add_edge("agente_info", END)

# 3. Compilar con Memoria Persistente (MongoDB Asíncrono)
app_chatbot = workflow.compile(checkpointer=memory_saver)

# --- FUNCIÓN PRINCIPAL PARA FASTAPI ---
async def procesar_mensaje(
    session_id: str,
    mensaje: str,
    contexto_ubicacion: str
) -> str:
    """
    Punto de entrada para routes.py. Invoca el grafo de LangGraph.
    """
    
    # 1. ACTUALIZACIÓN DEL TTL (Manejo de Sesión)
    # Refrescamos la fecha de actividad para evitar que la sesión expire
    db = get_db()
    if db is not None:
        try:
            await db["sesiones_chat"].update_one(
                {"session_id": session_id},
                {"$set": {"fecha_ultima_actividad": datetime.now(timezone.utc)}},
                upsert=True # Crea el documento si es un usuario nuevo
            )
        except Exception as e:
            print(f"⚠️ Error actualizando TTL de la sesión: {e}")

    # 2. Configuración de LangGraph
    config = {"configurable": {"thread_id": session_id}}
    
    inputs = {
        "mensaje": mensaje,
        "contexto_ubicacion": contexto_ubicacion,
        "session_id": session_id
    }

    # 3. Ejecución Segura
    try:
        resultado = await app_chatbot.ainvoke(inputs, config=config)
        return resultado.get("respuesta", "Lo siento, ocurrió un error inesperado.")
    except Exception as e:
        print(f"❌ Error crítico en LangGraph/MongoDB: {e}")
        return "Tuve un problema técnico accediendo a la base de datos de mis memorias. Por favor, intenta de nuevo."