from groq import Groq
from app.core.config import settings
from app.core.vector_db import vector_db # <-- Importamos tu gestor de ChromaDB

client = Groq(api_key=settings.GROQ_API_KEY)

def obtener_respuesta_info(mensaje: str, historial: list) -> str:
    """
    Agente de Información con RAG integrado.
    Busca contexto en ChromaDB antes de enviarle la consulta a Groq.
    """
    
    # 1. Búsqueda Vectorial (RAG)
    # Buscamos en ChromaDB los 4 fragmentos más relevantes relacionados con el mensaje del usuario
    contexto_extraido = "No se encontró información en la base de datos."
    try:
        resultados = vector_db.search(query=mensaje, n_results=4)
        documentos = resultados.get("documents", [[]])[0]
        
        if documentos:
            # Unimos los textos encontrados separándolos por líneas
            contexto_extraido = "\n\n---\n\n".join(documentos)
            print(f"🔍 Contexto recuperado para la consulta: {mensaje}")
            
    except Exception as e:
        print(f"⚠️ Error buscando en ChromaDB: {e}")

    # 2. Construcción del Prompt con el contexto inyectado
    system_prompt = f"""
    Eres un asistente especializado del Instituto Politécnico Nacional (IPN).
    Tu objetivo es responder las dudas del usuario basándote ÚNICAMENTE en la siguiente información oficial recuperada de la base de datos.
    
    INFORMACIÓN OFICIAL RECUPERADA:
    {contexto_extraido}
    
    Reglas:
    1. Responde de forma clara, concisa y útil (máximo 3 párrafos).
    2. Usa el contexto proporcionado para responder.
    3. Si el contexto menciona a la institución pero no la frase exacta, intenta resumir lo que hace la escuela basándote en la descripción disponible.
    4. Solo si no hay NINGUNA mención de la escuela o el tema en el contexto, di que no tienes la información exacta.
    5. NUNCA inventes datos, fechas de inscripción, ni nombres de programas que no estén en el texto recuperado.
    """

    # 3. Ensamblar los mensajes (Prompt + Historial + Mensaje actual)
    mensajes = [{"role": "system", "content": system_prompt}]
    mensajes.extend(historial)
    mensajes.append({"role": "user", "content": mensaje})

    # 4. Llamada al LLM (Groq)
    try:
        response = client.chat.completions.create(
            model=settings.MODELO_CHAT,
            messages=mensajes,
            temperature=0.3, # Bajamos la temperatura a 0.3 para hacer las respuestas más precisas y menos creativas
            max_tokens=400
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ Error en Agente Info: {e}")
        return "Lo siento, tuve un problema al procesar tu consulta en este momento."