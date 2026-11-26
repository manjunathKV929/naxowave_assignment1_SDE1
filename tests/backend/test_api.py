import pytest
import pytest_asyncio
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.session import Base, get_db
from backend.app.models.doctor import Doctor
from backend.app.models.slot import Slot

from sqlalchemy.pool import StaticPool

@pytest.fixture(scope="function")
def test_db():
    """Create an isolated in-memory database and populate test doctors and slots."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    # Seed test doctors
    doc1 = Doctor(
        id="doc_test_1",
        name="Dr. Priya Rao",
        speciality="Cardiology",
        bio="Cardiologist",
        active=1
    )
    doc2 = Doctor(
        id="doc_test_2",
        name="Dr. Marcus Vance",
        speciality="Dermatology",
        bio="Dermatologist",
        active=1
    )
    db.add_all([doc1, doc2])

    # Seed test slots
    slot1 = Slot(id="slot_t_1", doctor_id="doc_test_1", slot_date="2026-11-26", slot_time="10:00", status="available")
    slot2 = Slot(id="slot_t_2", doctor_id="doc_test_1", slot_date="2026-11-26", slot_time="11:30", status="available")
    slot3 = Slot(id="slot_t_3", doctor_id="doc_test_2", slot_date="2026-11-26", slot_time="14:00", status="available")
    db.add_all([slot1, slot2, slot3])

    db.commit()

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    """Async test client with dependency override for get_db."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

# =============================================================================
# 1. Health & Doctors Endpoints
# =============================================================================
@pytest.mark.asyncio
async def test_api_health(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_get_doctors(client):
    res = await client.get("/api/doctors")
    assert res.status_code == 200
    data = res.json()
    assert "doctors" in data
    assert len(data["doctors"]) == 2
    assert data["doctors"][0]["name"] in ["Dr. Priya Rao", "Dr. Marcus Vance"]

@pytest.mark.asyncio
async def test_get_doctor_by_id_found(client):
    res = await client.get("/api/doctors/doc_test_1")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "doc_test_1"
    assert data["speciality"] == "Cardiology"

@pytest.mark.asyncio
async def test_get_doctor_by_id_not_found(client):
    res = await client.get("/api/doctors/doc_non_existent")
    assert res.status_code == 404
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DOCTOR_NOT_FOUND"

# =============================================================================
# 2. Availability Endpoints
# =============================================================================
@pytest.mark.asyncio
async def test_get_doctor_availability(client):
    res = await client.get("/api/doctors/doc_test_1/availability?date=2026-11-26")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["doctor_id"] == "doc_test_1"
    assert len(data["slots"]) == 2

@pytest.mark.asyncio
async def test_search_availability_by_speciality(client):
    res = await client.get("/api/availability?speciality=cardiology")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["availability"]) == 1
    assert data["availability"][0]["doctor_id"] == "doc_test_1"

# =============================================================================
# 3. Appointment Booking & Double Booking Rejection
# =============================================================================
@pytest.mark.asyncio
async def test_book_appointment_complete_flow(client):
    # 1. Book successfully
    payload = {
        "phone_number": "9876543210",
        "doctor_id": "doc_test_1",
        "slot_id": "slot_t_1"
    }
    res = await client.post("/api/appointments", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    apt = data["appointment"]
    assert apt["status"] == "confirmed"
    assert apt["doctor_name"] == "Dr. Priya Rao"
    assert apt["phone_number_masked"] == "******3210"
    apt_id = apt["id"]

    # 2. Verify slot is no longer returned in availability
    avail_res = await client.get("/api/doctors/doc_test_1/availability?date=2026-11-26")
    avail_slots = [s["id"] for s in avail_res.json()["slots"]]
    assert "slot_t_1" not in avail_slots
    assert "slot_t_2" in avail_slots

    # 3. Attempt double booking on the same slot -> expect 409
    double_res = await client.post("/api/appointments", json={
        "phone_number": "9123456780",
        "doctor_id": "doc_test_1",
        "slot_id": "slot_t_1"
    })
    assert double_res.status_code == 409
    err = double_res.json()
    assert err["success"] is False
    assert err["error"]["code"] == "SLOT_UNAVAILABLE"

    # 4. Cancel appointment by ID
    cancel_res = await client.post(f"/api/appointments/{apt_id}/cancel")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["success"] is True
    assert cancel_data["status"] == "cancelled"

    # 5. Verify slot is restored to available
    avail_res2 = await client.get("/api/doctors/doc_test_1/availability?date=2026-11-26")
    avail_slots2 = [s["id"] for s in avail_res2.json()["slots"]]
    assert "slot_t_1" in avail_slots2

@pytest.mark.asyncio
async def test_book_appointment_validation_errors(client):
    # Invalid phone number
    res1 = await client.post("/api/appointments", json={
        "phone_number": "123",
        "doctor_id": "doc_test_1",
        "slot_id": "slot_t_1"
    })
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "VALIDATION_ERROR"

    # Non-existent doctor
    res2 = await client.post("/api/appointments", json={
        "phone_number": "9876543210",
        "doctor_id": "doc_non_existent",
        "slot_id": "slot_t_1"
    })
    assert res2.status_code == 404
    assert res2.json()["error"]["code"] == "DOCTOR_NOT_FOUND"

# =============================================================================
# 4. Cancellation by Phone & Edge Cases
# =============================================================================
@pytest.mark.asyncio
async def test_cancel_appointment_by_phone(client):
    # Book first
    await client.post("/api/appointments", json={
        "phone_number": "9876543210",
        "doctor_id": "doc_test_2",
        "slot_id": "slot_t_3"
    })

    # Cancel using phone number payload
    res = await client.post("/api/appointments/cancel", json={
        "phone_number": "987-654-3210"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["status"] == "cancelled"

    # Cancelling again returns 409 APPOINTMENT_ALREADY_CANCELLED
    res2 = await client.post("/api/appointments/cancel", json={
        "phone_number": "987-654-3210"
    })
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "APPOINTMENT_ALREADY_CANCELLED"

@pytest.mark.asyncio
async def test_cancel_unknown_phone_returns_404(client):
    res = await client.post("/api/appointments/cancel", json={
        "phone_number": "9999999999"
    })
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "APPOINTMENT_NOT_FOUND"

# =============================================================================
# 5. Dashboard Listings & Activity Feed
# =============================================================================
@pytest.mark.asyncio
async def test_get_appointments_dashboard_view(client):
    # Book an appointment
    await client.post("/api/appointments", json={
        "phone_number": "9876543210",
        "doctor_id": "doc_test_1",
        "slot_id": "slot_t_2"
    })

    res = await client.get("/api/appointments")
    assert res.status_code == 200
    data = res.json()
    assert "appointments" in data
    assert len(data["appointments"]) == 1
    apt = data["appointments"][0]
    # Phone must be masked for privacy
    assert apt["phone_number_masked"] == "******3210"
    assert "9876543210" not in apt["phone_number_masked"]
    assert apt["doctor_name"] == "Dr. Priya Rao"

@pytest.mark.asyncio
async def test_get_activity_feed(client):
    # Book and cancel to generate activity events
    await client.post("/api/appointments", json={
        "phone_number": "9876543210",
        "doctor_id": "doc_test_1",
        "slot_id": "slot_t_2"
    })
    await client.post("/api/appointments/cancel", json={
        "phone_number": "9876543210"
    })

    res = await client.get("/api/activity")
    assert res.status_code == 200
    events = res.json()["events"]
    assert len(events) >= 2
    types = [e["event_type"] for e in events]
    assert "appointment.created" in types
    assert "appointment.cancelled" in types

# =============================================================================
# 6. Voice Session Initializer
# =============================================================================
@pytest.mark.asyncio
async def test_voice_session_endpoint(client):
    res = await client.post("/api/voice/session")
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert data["status"] == "ready"
    assert "ws_url" in data

# =============================================================================
# 7. Security & Injection Resilience Tests
# =============================================================================
@pytest.mark.asyncio
async def test_sql_injection_and_security_handling(client):
    # SQL injection attempt in speciality query
    res = await client.get("/api/availability?speciality=' OR '1'='1")
    assert res.status_code == 200
    data = res.json()
    # Safely handled without leaking rows or breaking
    assert data["success"] is True
    assert len(data["availability"]) == 0

    # Malicious XSS payload in phone number
    res_xss = await client.post("/api/appointments", json={
        "phone_number": "<script>alert('xss')</script>",
        "doctor_id": "doc_test_1",
        "slot_id": "slot_t_1"
    })
    assert res_xss.status_code == 422
    err_data = res_xss.json()
    assert err_data["success"] is False
    assert err_data["error"]["code"] == "VALIDATION_ERROR"
    # Ensure no internal Python stack traces leaked
    assert "Traceback" not in str(err_data)
