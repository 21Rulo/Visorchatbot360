import json
import asyncio
from app.core.config import SharedResources
from app.core.vector_db import vector_db
from app.models.schemas import AgentState, Institucion
from app.core.utils import llamar_llm_con_reintentos

async def nodo_analista_ipn(state: AgentState) -> dict:
    """Extrae la intención de búsqueda y la institución"""
    client = SharedResources.get_groq_client()
    historial_texto = "\n".join([f"{msg['role']}: {msg['content']}" for msg in state.get("historial", [])[-4:]])
    
    prompt = f"""
    Eres un analista de consultas del IPN. Analiza el último mensaje y el historial.
    Contexto de la vista actual del usuario: {state.get('contexto_ubicacion', 'Sin contexto visual')}
    
    Historial: {historial_texto}
    Último mensaje: {state['mensaje']}
    
    Reglas:
    1. "consulta_optimizada": Reescribe el mensaje para buscar en una base vectorial. 
    2. "institucion": Extrae la escuela (ESFM, ESIT, ESIMEZ, etc.). Si no aplica, usa "GENERAL".
    
    Responde ÚNICAMENTE con JSON: {{"consulta_optimizada": "texto", "institucion": "SIGLAS"}}
    """
    
    try:
        res = await llamar_llm_con_reintentos([{"role": "user", "content": prompt}], client, {"type": "json_object"})
        analisis = json.loads(res.choices[0].message.content)
    except Exception:
        analisis = {"consulta_optimizada": state["mensaje"], "institucion": "GENERAL"}

    try:
        institucion_detectada = Institucion(analisis.get("institucion", "GENERAL").upper())
    except ValueError:
        institucion_detectada = Institucion.GENERAL

    # Pasamos la info al siguiente nodo
    return {
        "query_optimizada": analisis.get("consulta_optimizada", state["mensaje"]),
        "institucion": institucion_detectada.value
    }


# --- NODO 2: RECUPERADOR (Tu ChromaDB) ---
async def nodo_recuperador_chroma(state: AgentState) -> dict:
    """Ejecuta la búsqueda vectorial sin bloquear FastAPI"""
    query = state.get("query_optimizada", state["mensaje"])
    inst = state.get("institucion", "GENERAL")
    filtro = inst if inst != "GENERAL" else None
    
    print(f"🔍 ChromaDB -> Query: '{query}' | Inst: {filtro}")
    contexto = "No se encontró información en la base de datos oficial."
    
    try:
        resultados = await asyncio.to_thread(
            vector_db.search, 
            query=query, 
            n_results=3, 
            institucion=filtro
        )
        documentos = resultados.get("documents", [[]])[0]
        if documentos:
            contexto = "\n\n---\n\n".join(documentos)
    except Exception as e:
        print(f"⚠️ Error ChromaDB: {e}")

    # Pasamos los documentos al generador
    return {"documentos_recuperados": contexto}


# --- NODO 3: SÍNTESIS (La personalidad de Jasper del Legacy) ---
async def nodo_sintesis_jasper(state: AgentState) -> dict:
    """Genera la respuesta aplicando las reglas estrictas del IPN"""
    client = SharedResources.get_groq_client()
    
    # EL PROMPT DORADO RESCATADO DEL LEGACY
    system_prompt = f"""
    Eres Jasper, el guía virtual institucional, amable, profesional y accesible del IPN.
    
    ESCENA ACTUAL DEL USUARIO EN EL VISOR 360:
    {state.get('contexto_ubicacion', 'Sin contexto específico')}
    
    INFORMACIÓN INSTITUCIONAL RECUPERADA:
    {state.get('documentos_recuperados', '')}
    
    REGLAS ESTRICTAS:
    1. NO repitas el contexto visual a menos que sea útil para la pregunta.
    2. NUNCA menciones que eres una IA, un modelo o un bot.
    3. NO uses formato especial (cero markdown, asteriscos o listas gigantes). Escribe en texto plano conversacional.
    4. Usa frases cortas. Responde claro y conciso para jóvenes.
    5. Si la pregunta es sobre el escenario/recorrido actual, MÁXIMO 30 PALABRAS.
    6. Basa tu respuesta SOLO en la información recuperada.
    """

    mensajes = [{"role": "system", "content": system_prompt}]
    mensajes.extend(state.get("historial", []))
    mensajes.append({"role": "user", "content": state["mensaje"]})

    try:
        res = await llamar_llm_con_reintentos(mensajes, client)
        respuesta = res.choices[0].message.content
    except Exception:
        respuesta = "Tuve un pequeño problema procesando la información. ¿Puedes repetirlo?"

    return {
        "respuesta": respuesta,
        "historial": [
            {"role": "user", "content": state["mensaje"]},
            {"role": "assistant", "content": respuesta}
        ]
    }