from backend.app.api.doctors import router as doctors_router
from backend.app.api.appointments import router as appointments_router
from backend.app.api.activity import router as activity_router
from backend.app.api.voice import router as voice_router

__all__ = [
    "doctors_router",
    "appointments_router",
    "activity_router",
    "voice_router",
]
