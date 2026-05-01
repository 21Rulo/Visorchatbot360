import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.models.database import connect_to_mongo, close_mongo_connection

ENTORNO = os.getenv("ENTORNO", "desarrollo")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Esto ocurre al iniciar la App
    await connect_to_mongo()
    yield
    # Esto ocurre al apagar la App
    await close_mongo_connection()

app = FastAPI(
    title="Backend Chatbot 360",
    docs_url=None if ENTORNO == "produccion" else "/docs",
    redoc_url=None if ENTORNO == "produccion" else "/redoc",
    openapi_url=None if ENTORNO == "produccion" else "/openapi.json"
)

origenes_permitidos = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://tu-dominio-real.com"
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