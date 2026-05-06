from groq import Groq
from app.core.config import settings
from app.agents.agente_guia import obtener_respuesta_guia
from app.agents.agente_info import obtener_respuesta_info
from app.memory.short_term import obtener_historial, agregar_mensaje

client = Groq(api_key=settings.GROQ_API_KEY)

async def procesar_mensaje(
    session_id: str,
    mensaje: str, 
    contexto_ubicacion: str
) -> str:
    """
    Orquestador: clasifica la intención y enruta al agente correcto.
    Ahora maneja memoria de conversación por sesión.
    """
    system_prompt = """
    Eres el Orquestador del Chatbot del IPN. Tu único trabajo es clasificar la intención del usuario.
    Responde ÚNICAMENTE con UNA de estas palabras:
    - GUIA: Saludos, conversación general, preguntas sobre lo que ve en el recorrido virtual.
    - INFO: Preguntas sobre carreras, inscripciones, becas, servicios, trámites o cualquier 
            información institucional del IPN.
    No agregues explicaciones, puntos ni comillas. Solo la palabra.
    """

    historial = await obtener_historial(session_id)

    try:
        response = client.chat.completions.create(
            model=settings.MODELO_CHAT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": mensaje}
            ],
            temperature=0.0,
            max_tokens=10
        )
        
        intencion = response.choices[0].message.content.strip().upper()
        print(f"🧠 [ORQUESTADOR] session={session_id} | intención={intencion}")

        if "INFO" in intencion:
            respuesta = obtener_respuesta_info(mensaje, historial)
        else:
            respuesta = obtener_respuesta_guia(mensaje, contexto_ubicacion, historial)

    except Exception as e:
        print(f"Error en Orquestador: {e}")
        respuesta = obtener_respuesta_guia(mensaje, contexto_ubicacion, historial)

    # Guardamos el intercambio en memoria
    await agregar_mensaje(session_id, "user", mensaje)
    await agregar_mensaje(session_id, "assistant", respuesta)

    return respuesta