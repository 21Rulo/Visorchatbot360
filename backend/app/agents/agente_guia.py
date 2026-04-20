from groq import Groq
from app.core.config import settings

# Cliente oficial de Groq
client = Groq(api_key=settings.GROQ_API_KEY)

def obtener_respuesta_guia(mensaje: str, contexto_ubicacion: str) -> str:
    """
    Este agente toma el mensaje del usuario y el contexto de la escena 360
    para generar una respuesta inmersiva.
    """
    system_prompt = f"""
    Eres Jasper, el asistente virtual y guía del Instituto Politécnico Nacional (IPN).
    El usuario está haciendo un recorrido virtual 360° en este momento.

    UBICACIÓN ACTUAL DEL USUARIO:
    {contexto_ubicacion}

    Reglas:
    1. Responde de forma amable, útil y concisa (máximo 3 párrafos).
    2. Toma en cuenta la ubicación actual del usuario.
    3. Si el usuario te saluda, dale la bienvenida.
    """

    try:
        response = client.chat.completions.create(
            model=settings.MODELO_CHAT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": mensaje}
            ],
            temperature=0.7,
            max_tokens=300
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error en Agente Guía: {e}")
        return "Lo siento, tuve un problema de conexión."