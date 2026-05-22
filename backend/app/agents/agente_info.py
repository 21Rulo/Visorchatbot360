import json
import asyncio
import time
from app.core.config import SharedResources
from app.core.vector_db import vector_db
from app.models.schemas import AgentState, Institucion
from app.core.utils import llamar_llm_con_reintentos
from app.core.logger import logger

# --- NODO 1: ANALISTA (Con Inteligencia Legacy de Expansión) ---
@logger.catch
async def nodo_analista_ipn(state: AgentState) -> dict:
    """Extrae la institución y aplica Query Expansion para mejorar el RAG"""
    inicio = time.time()
    logger.info("Iniciando nodo_analista_ipn")
    
    client = SharedResources.get_groq_client()
    historial_texto = "\n".join([f"{msg['role']}: {msg['content']}" for msg in state.get("historial", [])[-4:]])
    
    prompt = f"""
    Eres un Analista Experto en Servicios y Asuntos Académicos del IPN.
    Tu objetivo es interpretar consultas (a veces ambiguas) de estudiantes y prepararlas para buscar en una base de datos vectorial oficial.

    Contexto visual actual: {state.get('contexto_ubicacion', 'Sin contexto visual')}
    Historial reciente: {historial_texto}
    Mensaje del usuario: "{state['mensaje']}"

    PASO 1: Interpreta la intención profunda del usuario. ¿Busca trámites, materias, becas, historia, ubicaciones?
    PASO 2: Expande la consulta (Query Expansion). Transforma su pregunta vaga en una cadena de búsqueda rica en palabras clave institucionales del IPN. Agrega sinónimos técnicos (ej. "dar de baja" -> "baja temporal, gestión escolar, reglamento").
    PASO 3: Detecta la unidad académica explícita o implícita en el contexto.

    Responde ÚNICAMENTE con un JSON válido con esta estructura:
    {{
        "consulta_optimizada": "Frase de búsqueda ampliada y llena de palabras clave institucionales",
        "institucion": "SIGLAS" (Usa ESFM, ESIT, ESIMEZ, etc. Si no aplica, usa "GENERAL")
    }}
    """
    
    try:
        res = await llamar_llm_con_reintentos([{"role": "user", "content": prompt}], client, {"type": "json_object"})
        analisis = json.loads(res.choices[0].message.content)
    except Exception as e:
        logger.error(f"Error en Analista IPN al llamar a Groq: {e}")
        analisis = {"consulta_optimizada": state["mensaje"], "institucion": "GENERAL"}

    try:
        institucion_detectada = Institucion(analisis.get("institucion", "GENERAL").upper())
    except ValueError:
        logger.warning(f"Institución '{analisis.get('institucion')}' no válida. Cayendo a GENERAL.")
        institucion_detectada = Institucion.GENERAL

    logger.debug(f"Pregunta original: {state['mensaje']}")
    logger.debug(f"Query Expandida: {analisis.get('consulta_optimizada')}")
    
    logger.success(f"Analista completado en {time.time() - inicio:.2f}s")

    return {
        "query_optimizada": analisis.get("consulta_optimizada", state["mensaje"]),
        "institucion": institucion_detectada.value
    }


# --- NODO 2: RECUPERADOR (ChromaDB Ultrarrápido) ---
@logger.catch
async def nodo_recuperador_chroma(state: AgentState) -> dict:
    """Ejecuta la búsqueda vectorial sin bloquear FastAPI"""
    inicio = time.time()
    
    query = state.get("query_optimizada", state["mensaje"])
    inst = state.get("institucion", "GENERAL")
    filtro = inst if inst != "GENERAL" else None
    
    logger.info(f"Iniciando búsqueda en ChromaDB | Query: '{query}' | Filtro: {filtro}")
    contexto = "No se encontró información oficial específica sobre este tema."
    
    try:
        resultados = await asyncio.to_thread(
            vector_db.search, 
            query=query, 
            n_results=3, 
            institucion=filtro
        )
        documentos = resultados.get("documents", [[]])[0]
        if documentos:
            contexto = "\n\n---\n\n".join(documentos)
            logger.info(f"Se recuperaron {len(documentos)} fragmentos de ChromaDB.")
        else:
            logger.warning("Búsqueda en ChromaDB no devolvió resultados.")
    except Exception as e:
        logger.error(f"Error accediendo a ChromaDB: {e}")

    logger.success(f"Recuperación completada en {time.time() - inicio:.2f}s")
    
    return {"documentos_recuperados": contexto}


# --- NODO 3: SÍNTESIS (El Jasper Institucional del Legacy) ---
@logger.catch
async def nodo_sintesis_jasper(state: AgentState) -> dict:
    """Genera la respuesta aplicando las reglas estrictas del IPN"""
    inicio = time.time()
    logger.info("Iniciando nodo_sintesis_jasper")
    
    client = SharedResources.get_groq_client()
    
    system_prompt = f"""
    Eres Jasper, el guía virtual institucional, amable, profesional y accesible del IPN.
    
    ESCENA ACTUAL DEL USUARIO EN EL VISOR 360:
    {state.get('contexto_ubicacion', 'Sin contexto específico')}
    
    INFORMACIÓN INSTITUCIONAL RECUPERADA (Usa esto como tu única fuente de verdad):
    {state.get('documentos_recuperados', '')}
    
    REGLAS ESTRICTAS:
    1. Si el usuario te saluda ("hola", "¿qué tal?"), DEVUELVE EL SALUDO amablemente antes de responder la pregunta.
    2. NUNCA menciones que eres una IA o un modelo de lenguaje.
    3. NO uses formato especial (cero markdown, asteriscos o listas gigantes). Escribe en texto plano conversacional.
    4. Usa frases cortas y claras. Responde para estudiantes y aspirantes jóvenes.
    5. No inventes procedimientos. Si la información recuperada dice "No se encontró información", dile al usuario amablemente que no tienes ese dato a la mano y recomiéndale ir a Servicios Escolares.
    """

    mensajes = [{"role": "system", "content": system_prompt}]
    mensajes.extend(state.get("historial", []))
    mensajes.append({"role": "user", "content": state["mensaje"]})

    try:
        res = await llamar_llm_con_reintentos(mensajes, client)
        respuesta = res.choices[0].message.content
        logger.info("Respuesta generada exitosamente por Groq")
    except Exception as e:
        logger.error(f"Error en Síntesis Jasper al llamar a Groq: {e}")
        respuesta = "Tuve un pequeño problema procesando los documentos oficiales. ¿Podemos intentarlo de nuevo?"

    logger.success(f"Síntesis completada en {time.time() - inicio:.2f}s")

    return {
        "respuesta": respuesta,
        "historial": [
            {"role": "user", "content": state["mensaje"]},
            {"role": "assistant", "content": respuesta}
        ]
    }