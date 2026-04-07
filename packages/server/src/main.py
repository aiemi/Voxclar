from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.core.exceptions import register_exception_handlers
from src.api.v1 import auth, users, meetings, transcripts, payments, profiles, asr_proxy, llm_proxy, referrals, asr_api, blog
from src.api.v1.blog_pages import router as blog_pages_router
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
    title="Voxclar API",
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
app.include_router(referrals.router, prefix="/api/v1/referrals", tags=["referrals"])
app.include_router(blog.router, prefix="/api/v1/blog", tags=["blog"])
app.include_router(asr_api.router, prefix="/v1", tags=["asr-api"])  # Public API: /v1/listen
app.include_router(ws_router, prefix="/api/v1/ws", tags=["websocket"])

# Server-rendered blog HTML + SEO (sitemap, robots, llms.txt)
app.include_router(blog_pages_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


from fastapi.responses import HTMLResponse  # noqa: E402

@app.get("/payment/result", response_class=HTMLResponse)
async def payment_result(success: str = "", cancelled: str = "", lifetime: str = "", topup: str = ""):
    if success:
        if lifetime:
            title, msg, color = "License Activated!", "Your Voxclar lifetime license is ready.", "#a855f7"
        elif topup:
            title, msg, color = "Time Added!", "+120 minutes have been added to your account.", "#22c55e"
        else:
            title, msg, color = "Subscribed!", "Your subscription is now active.", "#FFDD02"
    else:
        title, msg, color = "Payment Cancelled", "No charges were made.", "#888"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Voxclar — {title}</title>
<style>
  body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:#0a0a0a; color:#fff; font-family:-apple-system,sans-serif; }}
  .card {{ text-align:center; padding:60px 40px; border-radius:20px; background:#111;
           border:2px solid {color}33; max-width:420px; }}
  h1 {{ color:{color}; font-size:28px; margin:0 0 12px; }}
  p {{ color:#aaa; font-size:16px; margin:0 0 30px; line-height:1.5; }}
  .hint {{ color:#666; font-size:13px; }}
</style></head>
<body><div class="card">
  <h1>{title}</h1>
  <p>{msg}</p>
  <p class="hint">You can close this tab and return to Voxclar.</p>
</div></body></html>"""
