import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.routes import router as api_router
from app.models.database import connect_to_mongo, close_mongo_connection
from app.core.logger import logger

ENTORNO = os.getenv("ENTORNO", "desarrollo")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

# 1. INSTANCIAMOS FASTAPI UNA SOLA VEZ CON TODA LA CONFIGURACIÓN
app = FastAPI(
    title="Backend Chatbot 360",
    docs_url=None if ENTORNO == "produccion" else "/docs",
    redoc_url=None if ENTORNO == "produccion" else "/redoc",
    openapi_url=None if ENTORNO == "produccion" else "/openapi.json",
    lifespan=lifespan
)

# 2. APLICAMOS EL LIMITADOR A ESA ÚNICA INSTANCIA
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def manejador_amigable_rate_limit(request: Request, exc: RateLimitExceeded):
    logger.warning(f"🛡️ Rate limit excedido por IP: {request.client.host}")
    return JSONResponse(
        status_code=200,
        content={
            "respuesta": "¡Wow, vas muy rápido! 😅 Hay muchos visitantes explorando ahora mismo. Por favor, dame unos segunditos para procesar tus mensajes anteriores antes de continuar."
        }
    )

origenes_permitidos = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://visor.siis.ipn.mx",
    "https://www.visor.siis.ipn.mx",
    "https://ipn.mx",
    "https://www.ipn.mx"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ENTORNO == "desarrollo" else origenes_permitidos,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Visor 360 API activa"}