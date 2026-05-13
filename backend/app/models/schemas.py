from typing import TypedDict, List, Dict, Optional, Annotated
from enum import Enum

class Institucion(str, Enum):
    """Instituciones válidas basadas en tu knowledge_base"""
    ESFM = "ESFM"
    ESIT = "ESIT"
    CIITEC = "CIITEC"
    ESIMEZ = "ESIMEZ"
    CMPL = "CMPL"
    ENCB = "ENCB"
    GENERAL = "GENERAL"

def gestionar_historial(historial_actual: List[Dict[str, str]], nuevos_mensajes: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Suma los mensajes nuevos pero mantiene un límite estricto para no saturar 
    la memoria de MongoDB ni el contexto del LLM.
    """
    if not historial_actual:
        historial_actual = []
    if not nuevos_mensajes:
        nuevos_mensajes = []
        
    historial_combinado = historial_actual + nuevos_mensajes
    
    # Mantenemos solo los últimos 10 mensajes (5 interacciones completas)
    return historial_combinado[-10:]


class AgentState(TypedDict):
    """
    El 'State' de LangGraph. 
    Este diccionario viajará por todos los nodos (agentes).
    """
    # Datos de entrada
    session_id: str
    mensaje: str
    contexto_ubicacion: str
    
    # Memoria
    historial: Annotated[List[Dict[str, str]], gestionar_historial]
    
    # Datos generados durante el flujo
    intencion: Optional[str]
    institucion: Optional[str]
    respuesta: Optional[str]