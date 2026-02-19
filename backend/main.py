import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes.auth_routes import router as auth_router
from routes.admin_routes import router as admin_router
from routes.chat_routes import router as chat_router
from routes.rag_compat_routes import router as rag_compat_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database ready. Server starting.")
    yield
    logger.info("Server shutting down.")


app = FastAPI(
    title="Andreja - Agente Técnico de Elevadores",
    description="Sistema RAG com visão para manuais e apostilas de elevadores",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(rag_compat_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Andreja Backend"}


@app.get("/")
async def root():
    return {"message": "Andreja API - Documentação em /docs"}
