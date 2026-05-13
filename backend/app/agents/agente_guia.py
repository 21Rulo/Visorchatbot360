from app.core.config import settings, SharedResources
from app.models.schemas import AgentState
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

async def nodo_guia(state: AgentState) -> dict:
    """
    Nodo Guía: Conversación general y ubicación en el Visor 360.
    """
    client = SharedResources.get_groq_client()
    
    system_prompt = f"""
    Eres Jasper, el asistente virtual y guía del Instituto Politécnico Nacional (IPN).
    El usuario está haciendo un recorrido virtual 360° en este momento.

    UBICACIÓN ACTUAL DEL USUARIO:
    {state['contexto_ubicacion']}

    Reglas:
    1. Responde de forma amable, útil y concisa (máximo 3 párrafos).
    2. Toma en cuenta la ubicación actual del usuario.
    3. Si el usuario te saluda, dale la bienvenida.
    4. Recuerda lo que se ha hablado antes en la conversación.
    """

    # Construimos los mensajes con el historial del estado
    mensajes = [{"role": "system", "content": system_prompt}]
    if state.get("historial"):
        mensajes.extend(state["historial"])
    mensajes.append({"role": "user", "content": state["mensaje"]})

    try:
        response = await llamar_llm_con_reintentos(mensajes, client)
        respuesta_generada = response.choices[0].message.content
    except groq.RateLimitError:
        respuesta_generada = "Hay muchos alumnos usando el visor ahora mismo. Por favor, espera unos segundos y vuelve a preguntarme."
    except Exception as e:
        print(f"Error en Agente Guía: {e}")
        respuesta_generada = "Lo siento, tuve un problema de conexión."

    # Devolvemos SOLO lo que queremos actualizar en el AgentState
    return {
        "respuesta": respuesta_generada,
        "historial": [
            {"role": "user", "content": state["mensaje"]},
            {"role": "assistant", "content": respuesta_generada}
        ]
    }