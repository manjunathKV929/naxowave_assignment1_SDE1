import json
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.db.seed import seed_database
from backend.app.db.session import SessionLocal
from backend.app.models.slot import Slot
from voice_agent import (
    ALL_VOICE_TOOLS,
    CHECK_AVAILABILITY_SCHEMA,
    BOOK_APPOINTMENT_SCHEMA,
    CANCEL_APPOINTMENT_SCHEMA,
    execute_check_availability,
    execute_book_appointment,
    execute_cancel_appointment,
)

@pytest.fixture(autouse=True)
def setup_test_database():
    """Ensure seeded doctors and slots are available."""
    seed_database(reset=True)

# =============================================================================
# 1. Tool Schema Validation Tests
# =============================================================================
def test_voice_tools_schemas():
    assert len(ALL_VOICE_TOOLS) == 3
    names = [t.name for t in ALL_VOICE_TOOLS]
    assert "check_doctor_availability" in names
    assert "book_appointment" in names
    assert "cancel_appointment" in names

    book_dict = BOOK_APPOINTMENT_SCHEMA.to_default_dict()
    assert "phone_number" in book_dict["parameters"]["required"]
    assert "doctor_id" in book_dict["parameters"]["required"]
    assert "slot_id" in book_dict["parameters"]["required"]

# =============================================================================
# 2. Tool Service Execution Tests
# =============================================================================
def test_execute_check_availability():
    res = execute_check_availability(speciality="Cardiology")
    assert res["success"] is True
    assert len(res["availability"]) > 0
    first = res["availability"][0]
    assert first["speciality"] == "Cardiology"
    assert len(first["slots"]) > 0

def test_execute_book_appointment_phone_confirmation_required():
    avail = execute_check_availability(speciality="Cardiology")
    doc_id = avail["availability"][0]["doctor_id"]
    slot_id = avail["availability"][0]["slots"][0]["id"]

    # Fails if phone not verbally confirmed
    res_unconfirmed = execute_book_appointment(
        phone_number="9876543210",
        doctor_id=doc_id,
        slot_id=slot_id,
        phone_confirmed=False
    )
    assert res_unconfirmed["success"] is False
    assert res_unconfirmed["error"]["code"] == "CONFIRMATION_REQUIRED"

def test_execute_booking_and_cancellation_flow():
    avail = execute_check_availability(speciality="Cardiology")
    doc_id = avail["availability"][0]["doctor_id"]
    slot_id = avail["availability"][0]["slots"][0]["id"]

    # 1. Successful booking
    book_res = execute_book_appointment(
        phone_number="9876543210",
        doctor_id=doc_id,
        slot_id=slot_id,
        phone_confirmed=True
    )
    assert book_res["success"] is True
    assert book_res["status"] == "confirmed"
    apt_id = book_res["appointment_id"]

    # 2. Attempt double booking -> must fail
    double_res = execute_book_appointment(
        phone_number="9123456789",
        doctor_id=doc_id,
        slot_id=slot_id,
        phone_confirmed=True
    )
    assert double_res["success"] is False
    assert double_res["error"]["code"] == "SLOT_UNAVAILABLE"

    # 3. Successful cancellation
    cancel_res = execute_cancel_appointment(
        phone_number="9876543210",
        appointment_id=apt_id,
        phone_confirmed=True
    )
    assert cancel_res["success"] is True
    assert cancel_res["status"] == "cancelled"

# =============================================================================
# 3. End-to-End Complete Voice Conversation Tool Flow
# =============================================================================
def test_voice_conversation_complete_booking_and_cancellation():
    client = TestClient(app)

    with client.websocket_connect("/api/voice/ws?session_id=call_flow_01") as ws:
        # Initial connect events
        ev_start = json.loads(ws.receive_text())
        assert ev_start["type"] == "call.started"
        ev_conn = json.loads(ws.receive_text())
        assert ev_conn["type"] == "call.connected"
        ev_greet = json.loads(ws.receive_text())
        assert ev_greet["type"] == "transcript.agent"

        # Step 1: User asks for a cardiologist
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "I need a cardiologist appointment"
        }))

        # Transcript event for user
        u1 = json.loads(ws.receive_text())
        assert u1["type"] == "transcript.user"

        # Tool started event for availability
        t_start = json.loads(ws.receive_text())
        assert t_start["type"] == "tool.started"
        assert t_start["data"]["tool"] == "check_doctor_availability"

        # Tool completed event
        t_end = json.loads(ws.receive_text())
        assert t_end["type"] == "tool.completed"
        assert t_end["data"]["result"]["success"] is True

        # Agent speaks available options
        a1 = json.loads(ws.receive_text())
        assert a1["type"] == "transcript.agent"
        assert "Cardiology" in a1["data"]["text"]

        # Step 2: User provides phone number
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "9876543210"
        }))

        u2 = json.loads(ws.receive_text())
        assert u2["type"] == "transcript.user"

        # Agent repeats number digit-by-digit and asks for confirmation
        a2 = json.loads(ws.receive_text())
        assert a2["type"] == "transcript.agent"
        assert "confirm" in a2["data"]["text"].lower()

        # Step 3: User confirms verbally
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "Yes, that is correct."
        }))

        u3 = json.loads(ws.receive_text())
        assert u3["type"] == "transcript.user"

        # Tool started for booking
        t_book_start = json.loads(ws.receive_text())
        assert t_book_start["type"] == "tool.started"
        assert t_book_start["data"]["tool"] == "book_appointment"

        # Real-time appointment.created event broadcasted
        ev_created = json.loads(ws.receive_text())
        assert ev_created["type"] == "appointment.created"
        assert ev_created["data"]["status"] == "confirmed"

        # Tool completed event
        t_book_end = json.loads(ws.receive_text())
        assert t_book_end["type"] == "tool.completed"
        assert t_book_end["data"]["result"]["success"] is True

        # Agent announces confirmation
        a3 = json.loads(ws.receive_text())
        assert a3["type"] == "transcript.agent"
        assert "confirmed" in a3["data"]["text"].lower()

        # Step 4: User asks to cancel
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "I want to cancel my appointment"
        }))

        u4 = json.loads(ws.receive_text())
        assert u4["type"] == "transcript.user"

        a4 = json.loads(ws.receive_text())
        assert a4["type"] == "transcript.agent"
        assert "phone number" in a4["data"]["text"].lower()

        # Step 5: User speaks phone number for cancellation
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "9876543210"
        }))

        u5 = json.loads(ws.receive_text())
        assert u5["type"] == "transcript.user"

        a5 = json.loads(ws.receive_text())
        assert a5["type"] == "transcript.agent"
        assert "confirm" in a5["data"]["text"].lower()

        # Step 6: User confirms cancellation verbally
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "Yes, please cancel."
        }))

        u6 = json.loads(ws.receive_text())
        assert u6["type"] == "transcript.user"

        # Tool started for cancellation
        t_cancel_start = json.loads(ws.receive_text())
        assert t_cancel_start["type"] == "tool.started"
        assert t_cancel_start["data"]["tool"] == "cancel_appointment"

        # Real-time appointment.cancelled event broadcasted
        ev_cancelled = json.loads(ws.receive_text())
        assert ev_cancelled["type"] == "appointment.cancelled"
        assert ev_cancelled["data"]["status"] == "cancelled"

        # Tool completed event
        t_cancel_end = json.loads(ws.receive_text())
        assert t_cancel_end["type"] == "tool.completed"

        # Agent confirms cancellation
        a6 = json.loads(ws.receive_text())
        assert a6["type"] == "transcript.agent"
        assert "cancelled" in a6["data"]["text"].lower()

        # Step 7: End call
        ws.send_text(json.dumps({"type": "call.end"}))
        ev_end = json.loads(ws.receive_text())
        assert ev_end["type"] == "call.ended"

def test_voice_conversation_phone_rejection_flow():
    """Test edge case where user says 'no, that's wrong' during phone confirmation."""
    client = TestClient(app)

    with client.websocket_connect("/api/voice/ws?session_id=call_flow_reject_01") as ws:
        # Initial greeting events
        json.loads(ws.receive_text())  # call.started
        json.loads(ws.receive_text())  # call.connected
        json.loads(ws.receive_text())  # greeting transcript

        # 1. Ask for dermatologist
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "Are there any dermatologist appointments?"
        }))
        json.loads(ws.receive_text())  # transcript.user
        json.loads(ws.receive_text())  # tool.started
        json.loads(ws.receive_text())  # tool.completed
        json.loads(ws.receive_text())  # transcript.agent

        # 2. User gives wrong phone number first
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "1112223333"
        }))
        json.loads(ws.receive_text())  # transcript.user
        a_prompt = json.loads(ws.receive_text())  # transcript.agent asking confirmation
        assert "confirm" in a_prompt["data"]["text"].lower()

        # 3. User rejects: "No, that's wrong"
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "No, that's wrong"
        }))
        json.loads(ws.receive_text())  # transcript.user
        a_retry = json.loads(ws.receive_text())  # transcript.agent asking to repeat number
        assert "provide" in a_retry["data"]["text"].lower() or "repeat" in a_retry["data"]["text"].lower()

        # 4. User provides correct number
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "9876543210"
        }))
        json.loads(ws.receive_text())  # transcript.user
        json.loads(ws.receive_text())  # transcript.agent asking confirmation

        # 5. User confirms
        ws.send_text(json.dumps({
            "type": "text.input",
            "text": "Yes, that's correct"
        }))
        json.loads(ws.receive_text())  # transcript.user
        json.loads(ws.receive_text())  # tool.started (book_appointment)
        ev_created = json.loads(ws.receive_text())  # appointment.created
        assert ev_created["type"] == "appointment.created"
        assert ev_created["data"]["status"] == "confirmed"
        json.loads(ws.receive_text())  # tool.completed
        a_final = json.loads(ws.receive_text())  # transcript.agent
        assert "confirmed" in a_final["data"]["text"].lower()

        ws.send_text(json.dumps({"type": "call.end"}))
        assert json.loads(ws.receive_text())["type"] == "call.ended"
