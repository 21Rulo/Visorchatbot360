from groq import Groq
from app.core.config import settings
from app.agents.agente_guia import obtener_respuesta_guia

client = Groq(api_key=settings.GROQ_API_KEY)

def procesar_mensaje(mensaje: str, contexto_ubicacion: str) -> str:
    """
    Este es el ORQUESTADOR.
    Lee el mensaje del usuario, decide de qué tema trata y llama al agente correcto.
    """
    # 1. Prompt estricto para que la IA clasifique la intención
    system_prompt = """
    Eres el Orquestador del Chatbot del IPN. Tu único trabajo es clasificar la intención del usuario.
    Responde ÚNICAMENTE con UNA de estas palabras clave:
    - GUIA: Si el usuario saluda, platica, hace preguntas generales, o pregunta sobre lo que está viendo en su recorrido virtual.
    - ACADEMICO: Si el usuario pregunta por carreras, inscripciones o plan de estudios.
    - SERVICIOS: Si el usuario pregunta por becas, cafetería, deportes, etc.
    No agregues explicaciones, puntos ni comillas. Solo la palabra.
    """

    try:
        # 2. Le preguntamos a Groq qué tipo de mensaje es
        response = client.chat.completions.create(
            model=settings.MODELO_CHAT, # Usamos el modelo rápido para clasificar
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": mensaje}
            ],
            temperature=0.0, # Temperatura 0 para que no sea creativo, solo analítico
            max_tokens=10
        )
        
        # Limpiamos la respuesta por si la IA agregó un espacio
        intencion = response.choices[0].message.content.strip().upper()
        print(f"🧠 [ORQUESTADOR] Decidió que el mensaje es tipo: {intencion}")

        # 3. Enrutamos el mensaje según la intención detectada
        if "ACADEMICO" in intencion:
            # TODO: En el futuro aquí llamarás a "return obtener_respuesta_academica(mensaje)"
            return "Aún estoy aprendiendo sobre la oferta académica del IPN. Por el momento solo puedo guiarte en este recorrido virtual."
            
        elif "SERVICIOS" in intencion:
            # TODO: En el futuro llamarás al agente de servicios
            return "Todavía no tengo la información sobre becas o trámites, ¡pero pronto la tendré!"
            
        else:
            # Si dice "GUIA" o cualquier otra cosa, le pasamos la bolita al Agente Guía
            return obtener_respuesta_guia(mensaje, contexto_ubicacion)

    except Exception as e:
        print(f"Error en Orquestador: {e}")
        # Seguro de vida: Si el orquestador falla, mandamos todo al Guía para que el usuario no vea error
        return obtener_respuesta_guia(mensaje, contexto_ubicacion)