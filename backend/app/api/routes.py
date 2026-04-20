from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.agente_control import procesar_mensaje

router = APIRouter()

class MensajeChat(BaseModel):
    mensaje: str
    contexto: str

@router.post("/chat")
async def endpoint_chat(datos: MensajeChat):
    respuesta = procesar_mensaje(datos.mensaje, datos.contexto)
    return {"respuesta": respuesta}