from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from app.agents.agente_control import procesar_mensaje

router = APIRouter()

class MensajeChat(BaseModel):
    mensaje: str
    contexto: str
    session_id: str | None = None  # opcional: el frontend lo genera y lo guarda

@router.post("/chat")
async def endpoint_chat(datos: MensajeChat):
    # Si el frontend no manda session_id, generamos uno
    session_id = datos.session_id or str(uuid.uuid4())
    
    respuesta = await procesar_mensaje(
        session_id=session_id,
        mensaje=datos.mensaje,
        contexto_ubicacion=datos.contexto
    )
    
    return {
        "respuesta": respuesta,
        "session_id": session_id  # lo devolvemos para que el frontend lo guarde
    }