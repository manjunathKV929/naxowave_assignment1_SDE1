import sys
from pathlib import Path

_voice_dir = str((Path(__file__).parent / ".." / "voice-agent").resolve())
if _voice_dir not in sys.path:
    sys.path.insert(0, _voice_dir)

from agent import CareFlowVoiceAgent, CareFlowVoiceSession
from config import VoiceConfig
from prompts import CAREFLOW_VOICE_SYSTEM_PROMPT, CAREFLOW_INITIAL_GREETING
from tools import (
    ALL_VOICE_TOOLS,
    CHECK_AVAILABILITY_SCHEMA,
    BOOK_APPOINTMENT_SCHEMA,
    CANCEL_APPOINTMENT_SCHEMA,
    execute_check_availability,
    execute_book_appointment,
    execute_cancel_appointment,
)

__all__ = [
    "CareFlowVoiceAgent",
    "CareFlowVoiceSession",
    "VoiceConfig",
    "CAREFLOW_VOICE_SYSTEM_PROMPT",
    "CAREFLOW_INITIAL_GREETING",
    "ALL_VOICE_TOOLS",
    "CHECK_AVAILABILITY_SCHEMA",
    "BOOK_APPOINTMENT_SCHEMA",
    "CANCEL_APPOINTMENT_SCHEMA",
    "execute_check_availability",
    "execute_book_appointment",
    "execute_cancel_appointment",
]
