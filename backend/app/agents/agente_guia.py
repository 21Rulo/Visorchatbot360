import groq
import time
from app.core.config import SharedResources
from app.models.schemas import AgentState
from app.core.logger import logger
from app.core.utils import llamar_llm_con_reintentos

@logger.catch
async def nodo_guia(state: AgentState) -> dict:
    """
    Nodo Guía: Conversación general, saludos y ubicación en el Visor 360.
    Aplica las reglas estrictas de personalidad y longitud.
    """
    inicio = time.time()
    logger.info("Iniciando nodo_guia")
    
    client = SharedResources.get_groq_client()
    
    # EL SÚPER PROMPT DEL GUÍA: Restrictivo, con personalidad y límites claros
    system_prompt = f"""
    Eres Jasper, el guía virtual institucional del Instituto Politécnico Nacional (IPN). 
    Acompañas a los visitantes de forma amigable y entusiasta durante su recorrido virtual 360°.

    UBICACIÓN ACTUAL DEL USUARIO EN EL VISOR:
    {state.get('contexto_ubicacion', 'El usuario está navegando por el IPN.')}

    REGLAS ESTRICTAS DE TU ROL:
    1. Eres EXCLUSIVAMENTE un guía turístico. BAJO NINGUNA CIRCUNSTANCIA puedes escribir código de programación, resolver matemáticas, dar recetas ni ofrecer explicaciones técnicas complejas. Si te lo piden, declina educadamente recordando tu rol como guía del IPN.
    2. NUNCA menciones que eres una IA, un modelo de lenguaje o un bot. Eres Jasper.
    3. Tu tono debe ser alegre, directo, natural y dirigido a jóvenes.
    4. Tus respuestas deben ser MUY BREVES. Actúa como si estuvieras platicando mientras caminan. MÁXIMO 30 PALABRAS.
    5. NO uses formato especial (cero markdown, negritas o viñetas). Escribe en texto plano y conversacional.
    6. Si no hay mensajes previos en el historial, da una cálida bienvenida al espacio actual e invita a explorarlo.
    """

    mensajes = [{"role": "system", "content": system_prompt}]
    if state.get("historial"):
        mensajes.extend(state["historial"])
    mensajes.append({"role": "user", "content": state["mensaje"]})

    try:
        response = await llamar_llm_con_reintentos(mensajes, client)
        respuesta_generada = response.choices[0].message.content
    except groq.RateLimitError:
        respuesta_generada = "Hay muchos visitantes explorando el recorrido ahora mismo. Por favor, dame unos segundos y vuelve a preguntarme."
    except Exception as e:
        logger.error(f"⚠️ Error en Agente Guía: {e}")
        respuesta_generada = "Tuve una pequeña interrupción en mi conexión. ¿Podemos seguir con el recorrido?"

    logger.success(f"Agente Guía completado en {time.time() - inicio:.2f}s")

    return {
        "respuesta": respuesta_generada,
        "historial": [
            {"role": "user", "content": state["mensaje"]},
            {"role": "assistant", "content": respuesta_generada}
        ]
    }