import json
from groq import Groq
from app.core.config import settings
from app.core.vector_db import vector_db

client = Groq(api_key=settings.GROQ_API_KEY)

def reescribir_consulta(mensaje: str, historial: list) -> dict:
    """
    Analiza el historial y el mensaje actual para crear una consulta de búsqueda perfecta
    y detectar de qué escuela se está hablando.
    """
    # Formatear el historial para que Groq lo entienda rápido
    historial_texto = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial[-4:]])
    
    prompt = f"""
    Eres un analista de consultas del IPN. Tu tarea es analizar el último mensaje del usuario y el historial reciente para extraer parámetros de búsqueda.
    
    Historial reciente:
    {historial_texto}
    
    Último mensaje del usuario: {mensaje}
    
    Reglas:
    1. "consulta_optimizada": Reescribe el mensaje del usuario para que sea una pregunta completa y clara para buscar en una base de datos.
    2. "institucion": Identifica la escuela mencionada (ESFM, ESIT, CIITEC, ESIMEZ, CMPL, ENCB). Si no se sabe o es general del IPN, escribe "GENERAL".
    
    Responde ÚNICAMENTE con un JSON válido, sin texto adicional:
    {{"consulta_optimizada": "texto", "institucion": "SIGLAS"}}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192", # Modelo rápido y eficiente para reescritura
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"} 
        )
        
        resultado = json.loads(response.choices[0].message.content)
        return resultado
    except Exception as e:
        print(f"⚠️ Error en reescritura: {e}")
        return {"consulta_optimizada": mensaje, "institucion": "GENERAL"}


def obtener_respuesta_info(mensaje: str, historial: list, contexto_ubicacion: str = None) -> str:
    """
    Agente de Información con RAG integrado y Reescritura de Consulta.
    """
    # 1. Reescribir la consulta para aislar la intención
    analisis = reescribir_consulta(mensaje, historial)
    query_optimizada = analisis.get("consulta_optimizada", mensaje)
    institucion_detectada = analisis.get("institucion", "GENERAL")
    
    # 2. Configurar el filtro
    filtro_institucion = None
    if institucion_detectada != "GENERAL":
        filtro_institucion = institucion_detectada
        print(f"🏫 Institución detectada por IA: {filtro_institucion}")
    else:
        print("🏫 Búsqueda general (sin filtro de institución)")
        
    print(f"🔍 Buscando en ChromaDB: '{query_optimizada}'")

    # 3. Búsqueda Vectorial (RAG)
    contexto_extraido = "No se encontró información en la base de datos."
    try:
        resultados = vector_db.search(query=query_optimizada, n_results=4, institucion=filtro_institucion)
        documentos = resultados.get("documents", [[]])[0]
        
        if documentos:
            contexto_extraido = "\n\n---\n\n".join(documentos)
            
    except Exception as e:
        print(f"⚠️ Error buscando en ChromaDB: {e}")

    # 4. Construcción del Prompt Final
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
    mensajes.extend(historial)
    mensajes.append({"role": "user", "content": mensaje})

    # 5. Llamada al LLM
    try:
        response = client.chat.completions.create(
            model=settings.MODELO_CHAT, 
            messages=mensajes,
            temperature=0.3, 
            max_tokens=400
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ Error en Agente Info: {e}")
        return "Lo siento, tuve un problema al procesar tu consulta en este momento."