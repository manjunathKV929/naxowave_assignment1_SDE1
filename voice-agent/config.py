"""Configuration settings for CareFlow AI Voice Agent."""
import os
from dotenv import load_dotenv

load_dotenv()

class VoiceConfig:
    # API Keys
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Voice Settings
    # Default: Rachel voice (warm, professional, calm healthcare persona)
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    ELEVENLABS_MODEL_ID: str = "eleven_turbo_v2_5"

    # Gemini LLM Settings
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Audio Transport Parameters
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1

    # Voice Activity Detection (VAD)
    ENABLE_SILERO_VAD: bool = os.getenv("ENABLE_SILERO_VAD", "true").lower() in ("true", "1", "yes")

    # Server Settings
    HOST: str = os.getenv("VOICE_AGENT_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("VOICE_AGENT_PORT", "8000"))

    @classmethod
    def has_elevenlabs_key(cls) -> bool:
        return bool(cls.ELEVENLABS_API_KEY and not cls.ELEVENLABS_API_KEY.startswith("your_"))

    @classmethod
    def has_gemini_key(cls) -> bool:
        return bool(cls.GEMINI_API_KEY and not cls.GEMINI_API_KEY.startswith("your_"))

    @classmethod
    def is_fully_configured(cls) -> bool:
        return cls.has_elevenlabs_key() and cls.has_gemini_key()
