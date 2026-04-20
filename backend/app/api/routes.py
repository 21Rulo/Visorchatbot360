from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.agente_guia import obtener_respuesta_guia

router = APIRouter()

class MensajeChat(BaseModel):
    mensaje: str
    contexto: str

@router.post("/chat")
async def endpoint_chat(datos: MensajeChat):
    respuesta = obtener_respuesta_guia(datos.mensaje, datos.contexto)
    return {"respuesta": respuesta}