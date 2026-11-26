import os
import uuid
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/voice", tags=["voice"])

class VoiceSessionResponse(BaseModel):
    session_id: str
    status: str
    ws_url: str

@router.post("/session", response_model=VoiceSessionResponse)
def create_voice_session():
    """Initialize a voice agent session for client connection."""
    session_id = f"v_sess_{uuid.uuid4().hex[:12]}"
    voice_port = os.getenv("VOICE_AGENT_PORT", "8765")
    ws_url = f"ws://localhost:{voice_port}/ws"

    return {
        "session_id": session_id,
        "status": "ready",
        "ws_url": ws_url
    }
