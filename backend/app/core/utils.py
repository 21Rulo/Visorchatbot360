import groq
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from app.core.config import settings

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type(groq.RateLimitError),
    reraise=True
)
async def llamar_llm_con_reintentos(mensajes, client, response_format=None):
    """
    Función centralizada para llamar a Groq con protección contra Rate Limits.
    Soporta respuestas en texto plano o en formato JSON.
    """
    kwargs = {
        "model": settings.MODELO_CHAT,
        "messages": mensajes,
        # Si pedimos JSON, bajamos la temperatura para mayor precisión
        "temperature": 0.0 if response_format else 0.7, 
        "max_tokens": 300 if response_format else 400
    }
    
    if response_format:
        kwargs["response_format"] = response_format
        
    return await client.chat.completions.create(**kwargs)