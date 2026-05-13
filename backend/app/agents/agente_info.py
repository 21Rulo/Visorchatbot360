import json
import asyncio
from app.core.config import settings, SharedResources
from app.core.vector_db import vector_db
from app.models.schemas import AgentState, Institucion
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import groq

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type(groq.RateLimitError), # Solo reintenta si es por límite gratuito
    reraise=True # Si falla 4 veces, lanza el error para que nuestro try/except lo atrape
)

async def llamar_llm_con_reintentos(mensajes, client):
    """Función de apoyo para llamar a Groq con protección contra Rate Limits"""
    return await client.chat.completions.create(
        model=settings.MODELO_CHAT,
        messages=mensajes,
        temperature=0.7,
        max_tokens=300
    )

async def nodo_info(state: AgentState) -> dict:
    """
    Nodo de Información: RAG integrado y Reescritura de Consulta.
    """
    client = SharedResources.get_groq_client()
    mensaje_actual = state["mensaje"]
    historial = state.get("historial", [])
    
    # --- PASO 1: Reescritura ---
    historial_texto = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial[-4:]])
    prompt_reescritura = f"""
    Eres un analista de consultas del IPN. Analiza el último mensaje y el historial para extraer parámetros de búsqueda.
    
    Historial reciente:
    {historial_texto}
    
    Último mensaje: {mensaje_actual}
    
    Reglas:
    1. "consulta_optimizada": Reescribe el mensaje para buscar en una base de datos.
    2. "institucion": Identifica la escuela (ESFM, ESIT, CIITEC, ESIMEZ, CMPL, ENCB). Si es general, escribe "GENERAL".
    
    Responde ÚNICAMENTE con un JSON: {{"consulta_optimizada": "texto", "institucion": "SIGLAS"}}
    """
    
    try:
        res_reescritura = await client.chat.completions.create(
            model=settings.MODELO_CHAT,
            messages=[{"role": "user", "content": prompt_reescritura}],
            temperature=0.0,
            response_format={"type": "json_object"} 
        )
        analisis = json.loads(res_reescritura.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Error en reescritura: {e}")
        analisis = {"consulta_optimizada": mensaje_actual, "institucion": "GENERAL"}

    query_optimizada = analisis.get("consulta_optimizada", mensaje_actual)
    institucion_str = analisis.get("institucion", "GENERAL").upper()
    
    # Validación segura (Type-safe) con el Enum
    try:
        institucion_detectada = Institucion(institucion_str)
    except ValueError:
        institucion_detectada = Institucion.GENERAL

    filtro = institucion_detectada.value if institucion_detectada != Institucion.GENERAL else None
    print(f"🔍 Buscando en ChromaDB: '{query_optimizada}' | Filtro: {filtro}")

    # --- PASO 2: Búsqueda Vectorial ---
    contexto_extraido = "No se encontró información en la base de datos."
    try:
        # Asumo que vector_db.search es síncrono por tu código original
        resultados = await asyncio.to_thread(
            vector_db.search, 
            query=query_optimizada, 
            n_results=4, 
            institucion=filtro
        )
        documentos = resultados.get("documents", [[]])[0]
        if documentos:
            contexto_extraido = "\n\n---\n\n".join(documentos)
    except Exception as e:
        print(f"⚠️ Error buscando en ChromaDB: {e}")

    # --- PASO 3: Generación ---
    system_prompt = f"""
    Eres Jasper, un asistente especializado del Instituto Politécnico Nacional (IPN).
    Tu objetivo es responder las dudas del usuario basándote ÚNICAMENTE en la siguiente información oficial recuperada.
    
    INFORMACIÓN OFICIAL RECUPERADA:
    {contexto_extraido}
    
    Reglas:
    1. Responde de forma clara, concisa y útil (máximo 3 párrafos).
    2. Usa el contexto proporcionado para responder.
    3. Si la información no está en el contexto, di amablemente que no tienes el dato exacto, no lo inventes.
    """

    mensajes = [{"role": "system", "content": system_prompt}]
    if historial:
        mensajes.extend(historial)
    mensajes.append({"role": "user", "content": mensaje_actual})

    try:
        res_final = await client.chat.completions.create(
            model=settings.MODELO_CHAT, 
            messages=mensajes,
            temperature=0.3, 
            max_tokens=400
        )
        respuesta_generada = res_final.choices[0].message.content
    except Exception as e:
        print(f"❌ Error en Agente Info: {e}")
        respuesta_generada = "Lo siento, tuve un problema al procesar tu consulta."

    # Devolvemos la respuesta Y la institución detectada para guardarlo en el State
    return {
        "respuesta": respuesta_generada,
        "institucion": institucion_detectada.value,
        "historial": [
            {"role": "user", "content": state["mensaje"]},
            {"role": "assistant", "content": respuesta_generada}
        ]
    }