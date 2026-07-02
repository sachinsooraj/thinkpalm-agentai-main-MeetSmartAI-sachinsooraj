"""
MeetSmart AI — FastAPI application entry point.
Initialises DB, registers all routers, sets up CORS, and starts the scheduler.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.db.database import init_db
from src.agents.reminder_agent import reminder_agent
from src.api.routes import availability, booking, meetings, notes
from src.api.models import HealthResponse
from src.utils.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("🚀 MeetSmart AI starting up...")
    init_db()
    # Auto-refresh slots if expired (seed handles detection)
    try:
        from src.db.seed import seed as run_seed
        run_seed()
    except Exception as e:
        logger.warning(f"Slot refresh skipped: {e}")
    reminder_agent.start()
    logger.info("✅ Database initialised and Reminder Agent started.")
    yield
    logger.info("🛑 MeetSmart AI shutting down...")
    reminder_agent.stop()


app = FastAPI(
    title="MeetSmart AI",
    description=(
        "Internal Calendly-style meeting platform for ThinkPalm teams. "
        "Powered by AI agents for availability, booking, invites, notes, MoM, and reminders."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — allow React dev server ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.FRONTEND_PORT}",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(availability.router)
app.include_router(booking.router)
app.include_router(meetings.router)
app.include_router(notes.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version="1.0.0",
        gemini_enabled=settings.gemini_enabled,
        smtp_mode=settings.SMTP_MODE,
    )


@app.get("/", tags=["System"])
def root():
    return {
        "app": "MeetSmart AI",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "company": "ThinkPalm Technologies",
    }
