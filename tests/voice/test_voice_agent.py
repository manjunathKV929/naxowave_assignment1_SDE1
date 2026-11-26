import json
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from voice_agent import (
    VoiceConfig,
    CAREFLOW_VOICE_SYSTEM_PROMPT,
    CAREFLOW_INITIAL_GREETING,
    CareFlowVoiceAgent,
)

def test_voice_config_defaults():
    config = VoiceConfig()
    assert config.ELEVENLABS_VOICE_ID == "21m00Tcm4TlvDq8ikWAM"
    assert config.GEMINI_MODEL == "gemini-2.0-flash"
    assert config.AUDIO_SAMPLE_RATE == 16000
    assert config.AUDIO_CHANNELS == 1

def test_voice_prompt_safety_rules():
    assert "NEVER INVENT DOCTORS OR AVAILABILITY" in CAREFLOW_VOICE_SYSTEM_PROMPT
    assert "MANDATORY PHONE CONFIRMATION PROTOCOL" in CAREFLOW_VOICE_SYSTEM_PROMPT
    assert "Ask only ONE question at a time" in CAREFLOW_VOICE_SYSTEM_PROMPT
    assert "Do not provide medical diagnosis" in CAREFLOW_VOICE_SYSTEM_PROMPT

def test_voice_agent_initialization():
    agent = CareFlowVoiceAgent()
    assert agent is not None
    assert agent.config is not None
    assert agent.vad_analyzer is not None

def test_voice_websocket_lifecycle_and_turn_taking():
    client = TestClient(app)

    with client.websocket_connect("/api/voice/ws?session_id=test_sess_01") as websocket:
        # 1. First event: call.started
        msg1 = json.loads(websocket.receive_text())
        assert msg1["type"] == "call.started"
        assert msg1["data"]["session_id"] == "test_sess_01"

        # 2. Second event: call.connected
        msg2 = json.loads(websocket.receive_text())
        assert msg2["type"] == "call.connected"

        # 3. Third event: initial agent greeting transcript
        msg3 = json.loads(websocket.receive_text())
        assert msg3["type"] == "transcript.agent"
        assert "CareFlow" in msg3["data"]["text"]

        # 4. Simulate user speaking via text input event
        websocket.send_text(json.dumps({
            "type": "text.input",
            "text": "Hello, is there a cardiologist available?"
        }))

        # Expect user transcript reflection
        user_ev = json.loads(websocket.receive_text())
        assert user_ev["type"] == "transcript.user"
        assert "cardiologist" in user_ev["data"]["text"]

        # Expect tool execution events
        tool_start_ev = json.loads(websocket.receive_text())
        assert tool_start_ev["type"] == "tool.started"
        assert tool_start_ev["data"]["tool"] == "check_doctor_availability"

        tool_comp_ev = json.loads(websocket.receive_text())
        assert tool_comp_ev["type"] == "tool.completed"
        assert tool_comp_ev["data"]["tool"] == "check_doctor_availability"
        assert tool_comp_ev["data"]["result"]["success"] is True

        # Expect agent response transcript
        agent_ev = json.loads(websocket.receive_text())
        assert agent_ev["type"] == "transcript.agent"
        assert any(k in agent_ev["data"]["text"].lower() for k in ["priya rao", "cardiology", "available", "morning"])

        # 5. Client mute control
        websocket.send_text(json.dumps({
            "type": "client.mute",
            "muted": True
        }))

        # 6. End call
        websocket.send_text(json.dumps({
            "type": "call.end"
        }))

        # Expect call.ended
        end_ev = json.loads(websocket.receive_text())
        assert end_ev["type"] == "call.ended"
