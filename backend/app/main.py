import os
import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from voice_agent import CareFlowVoiceAgent
import uuid
from typing import Optional
from fastapi import WebSocket
from sqlalchemy import select

from backend.app.schemas.common import CareFlowException
from backend.app.api.doctors import router as doctors_router
from backend.app.api.appointments import router as appointments_router
from backend.app.api.activity import router as activity_router
from backend.app.api.voice import router as voice_router
from backend.app.db.session import SessionLocal
from backend.app.db.seed import seed_database
from backend.app.models.doctor import Doctor

load_dotenv()
logger = logging.getLogger("careflow")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-seed database if empty on startup
    try:
        db = SessionLocal()
        existing_doc = db.scalar(select(Doctor).limit(1))
        if not existing_doc:
            logger.info("Initializing and seeding database with doctors and slots...")
            seed_database(db=db, reset=False)
        db.close()
    except Exception as e:
        logger.warning(f"Could not auto-seed database on startup: {e}")
    yield

app = FastAPI(
    title="CareFlow AI API",
    description="Doctor appointment management and voice assistant backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Global Exception Handlers (Standardized JSON Format per API_SPEC.md)
# -----------------------------------------------------------------------------
@app.exception_handler(CareFlowException)
async def careflow_exception_handler(request: Request, exc: CareFlowException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error_msg = errors[0]["msg"] if errors else "Validation failed"
    # Clean up error message if prefixed with 'Value error, '
    if first_error_msg.startswith("Value error, "):
        first_error_msg = first_error_msg.replace("Value error, ", "")

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": first_error_msg
            }
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal server error occurred."
            }
        }
    )

# -----------------------------------------------------------------------------
# Route Registration
# -----------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    return {"status": "ok"}

app.include_router(doctors_router)
app.include_router(appointments_router)
app.include_router(activity_router)
app.include_router(voice_router)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

@app.websocket("/api/voice/ws")
@app.websocket("/ws")
async def voice_websocket_endpoint(websocket: WebSocket, session_id: Optional[str] = None):
    sid = session_id or f"sess_{uuid.uuid4().hex[:10]}"
    agent = CareFlowVoiceAgent()
    await agent.run_session(websocket, sid)

# Serve built frontend if available
dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if dist_dir.exists():
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api") or full_path.startswith("ws"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        file_path = dist_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_dir / "index.html")

