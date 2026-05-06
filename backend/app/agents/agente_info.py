from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def obtener_respuesta_info(mensaje: str, historial: list) -> str:
    """
    Agente de Información: responde preguntas académicas Y de servicios del IPN.
    Recibe el historial completo para mantener contexto de la conversación.
    """
    system_prompt = """
    Eres un asistente especializado del Instituto Politécnico Nacional (IPN).
    Respondes preguntas sobre:
    
    ACADÉMICO:
    - Carreras y programas de estudio (ingeniería, medicina, ciencias, etc.)
    - Proceso de admisión e inscripción
    - Planes de estudio y materias
    - Requisitos de titulación
    
    SERVICIOS:
    - Becas (tipos, requisitos, cómo aplicar)
    - Cafeterías y comedores
    - Actividades deportivas y culturales
    - Trámites escolares
    - Transporte y instalaciones

    Reglas:
    1. Sé claro, conciso y útil (máximo 3 párrafos).
    2. Si no tienes información exacta, dilo honestamente y sugiere 
       dónde puede encontrarla (sitio web del IPN, etc.).
    3. No inventes datos como fechas de inscripción o montos de beca.
    """

    # Construimos los mensajes con el historial incluido
    mensajes = [{"role": "system", "content": system_prompt}]
    mensajes.extend(historial)
    mensajes.append({"role": "user", "content": mensaje})

    try:
        response = client.chat.completions.create(
            model=settings.MODELO_CHAT,
            messages=mensajes,
            temperature=0.5,
            max_tokens=400
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error en Agente Info: {e}")
        return "Lo siento, tuve un problema al consultar esa información."