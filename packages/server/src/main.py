from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.core.exceptions import register_exception_handlers
from src.api.v1 import auth, users, meetings, transcripts, payments, profiles, asr_proxy, llm_proxy
from src.api.websocket import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    print(f"Starting {settings.APP_NAME} server...")
    yield
    # Shutdown
    print("Shutting down server...")


app = FastAPI(
    title="IMEET.AI API",
    version="2.0.0",
    description="AI-powered meeting assistant backend",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# API v1 routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(meetings.router, prefix="/api/v1/meetings", tags=["meetings"])
app.include_router(transcripts.router, prefix="/api/v1/transcripts", tags=["transcripts"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["profiles"])
app.include_router(asr_proxy.router, prefix="/api/v1/asr", tags=["asr"])
app.include_router(llm_proxy.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(ws_router, prefix="/api/v1/ws", tags=["websocket"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}
