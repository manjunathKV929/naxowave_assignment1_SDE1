import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.session import Base
from backend.app.models.doctor import Doctor
from backend.app.models.slot import Slot
from backend.app.models.appointment import Appointment
from backend.app.models.activity import ActivityEvent
from backend.app.services.appointment_service import AppointmentService
from backend.app.schemas.common import (
    normalize_phone_number,
    mask_phone_number,
    ValidationError,
    DoctorNotFoundError,
    SlotUnavailableError,
    AppointmentNotFoundError,
    AppointmentAlreadyCancelledError,
)

@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database for each test."""
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    # Seed baseline doctors
    doc1 = Doctor(
        id="doc_001",
        name="Dr. Priya Rao",
        speciality="Cardiology",
        bio="Cardiology specialist",
        active=1
    )
    doc2 = Doctor(
        id="doc_002",
        name="Dr. Marcus Vance",
        speciality="Dermatology",
        bio="Dermatologist",
        active=1
    )
    session.add_all([doc1, doc2])

    # Seed baseline slots
    slot1 = Slot(id="slot_101", doctor_id="doc_001", slot_date="2026-11-25", slot_time="10:00", status="available")
    slot2 = Slot(id="slot_102", doctor_id="doc_001", slot_date="2026-11-25", slot_time="11:30", status="available")
    slot3 = Slot(id="slot_201", doctor_id="doc_002", slot_date="2026-11-25", slot_time="14:00", status="available")
    session.add_all([slot1, slot2, slot3])

    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=test_engine)

# =============================================================================
# 1. Phone Normalization & Masking Tests
# =============================================================================
def test_phone_normalization_valid():
    assert normalize_phone_number("9876543210") == "9876543210"
    assert normalize_phone_number("+1 (555) 234-5678") == "15552345678"
    assert normalize_phone_number(" 987-654-3210 ") == "9876543210"
    assert normalize_phone_number("987 654 3210") == "9876543210"

def test_phone_normalization_invalid():
    with pytest.raises(ValidationError):
        normalize_phone_number("12345")  # Too short (< 7)
    with pytest.raises(ValidationError):
        normalize_phone_number("abcdefghijk")  # No digits
    with pytest.raises(ValidationError):
        normalize_phone_number("")  # Empty

def test_phone_masking():
    assert mask_phone_number("9876543210") == "******3210"
    assert mask_phone_number("15552345678") == "*******5678"
    assert mask_phone_number("1234") == "****"

# =============================================================================
# 2. Doctor Queries Tests
# =============================================================================
def test_get_doctors(db_session):
    service = AppointmentService(db_session)
    doctors = service.get_doctors()
    assert len(doctors) == 2
    assert any(d.name == "Dr. Priya Rao" for d in doctors)

def test_get_doctor_by_id_success(db_session):
    service = AppointmentService(db_session)
    doctor = service.get_doctor_by_id("doc_001")
    assert doctor.name == "Dr. Priya Rao"
    assert doctor.speciality == "Cardiology"

def test_get_doctor_by_id_not_found(db_session):
    service = AppointmentService(db_session)
    with pytest.raises(DoctorNotFoundError):
        service.get_doctor_by_id("doc_non_existent")

# =============================================================================
# 3. Availability Queries Tests
# =============================================================================
def test_check_availability_by_doctor(db_session):
    service = AppointmentService(db_session)
    avail = service.check_availability(doctor_id="doc_001")
    assert len(avail) >= 1
    assert avail[0]["doctor_id"] == "doc_001"
    assert len(avail[0]["slots"]) == 2

def test_check_availability_by_speciality(db_session):
    service = AppointmentService(db_session)
    avail = service.check_availability(speciality="dermatology")
    assert len(avail) == 1
    assert avail[0]["doctor_id"] == "doc_002"
    assert avail[0]["slots"][0]["id"] == "slot_201"

def test_check_availability_by_date(db_session):
    service = AppointmentService(db_session)
    avail = service.check_availability(date_str="2026-11-25")
    assert len(avail) == 2

    # Date with no slots
    avail_empty = service.check_availability(date_str="2099-01-01")
    assert len(avail_empty) == 0

# =============================================================================
# 4. Booking Happy Path Tests
# =============================================================================
def test_book_appointment_success(db_session):
    service = AppointmentService(db_session)
    result = service.book_appointment(
        phone_number="9876543210",
        doctor_id="doc_001",
        slot_id="slot_101"
    )

    assert result["success"] is True
    assert result["status"] == "confirmed"
    assert result["doctor_name"] == "Dr. Priya Rao"
    assert result["phone_number_masked"] == "******3210"

    # Verify slot is updated to booked
    slot = db_session.get(Slot, "slot_101")
    assert slot.status == "booked"

    # Verify activity event created
    events = service.get_activity_events()
    assert len(events) == 1
    assert events[0].event_type == "appointment.created"

# =============================================================================
# 5. Double Booking Prevention Tests
# =============================================================================
def test_double_booking_prevention(db_session):
    service = AppointmentService(db_session)
    # First booking
    res1 = service.book_appointment("9876543210", "doc_001", "slot_101")
    assert res1["success"] is True

    # Second booking attempt for same slot by different phone
    with pytest.raises(SlotUnavailableError) as exc_info:
        service.book_appointment("9123456789", "doc_001", "slot_101")
    assert "no longer available" in str(exc_info.value)

    # Second booking attempt by same phone
    with pytest.raises(SlotUnavailableError):
        service.book_appointment("9876543210", "doc_001", "slot_101")

# =============================================================================
# 6. Invalid Booking Input Tests
# =============================================================================
def test_book_with_invalid_doctor(db_session):
    service = AppointmentService(db_session)
    with pytest.raises(DoctorNotFoundError):
        service.book_appointment("9876543210", "doc_999", "slot_101")

def test_book_with_invalid_slot(db_session):
    service = AppointmentService(db_session)
    with pytest.raises(SlotUnavailableError):
        service.book_appointment("9876543210", "doc_001", "slot_non_existent")

def test_book_with_invalid_phone(db_session):
    service = AppointmentService(db_session)
    with pytest.raises(ValidationError):
        service.book_appointment("123", "doc_001", "slot_101")

# =============================================================================
# 7. Cancellation Happy Path Tests
# =============================================================================
def test_cancel_appointment_success(db_session):
    service = AppointmentService(db_session)
    # Book first
    booking = service.book_appointment("9876543210", "doc_001", "slot_101")
    apt_id = booking["appointment_id"]

    # Cancel using phone number
    cancel_res = service.cancel_appointment("9876543210")
    assert cancel_res["success"] is True
    assert cancel_res["appointment_id"] == apt_id
    assert cancel_res["status"] == "cancelled"

    # Verify slot is released back to available
    slot = db_session.get(Slot, "slot_101")
    assert slot.status == "available"

    # Verify activity events
    events = service.get_activity_events()
    assert len(events) == 2
    assert events[0].event_type == "appointment.cancelled"

# =============================================================================
# 8. Cancellation Edge Cases Tests
# =============================================================================
def test_cancel_non_existent_appointment(db_session):
    service = AppointmentService(db_session)
    with pytest.raises(AppointmentNotFoundError):
        service.cancel_appointment("9999999999")

def test_cancel_already_cancelled_appointment(db_session):
    service = AppointmentService(db_session)
    booking = service.book_appointment("9876543210", "doc_001", "slot_101")
    apt_id = booking["appointment_id"]

    # First cancellation succeeds
    service.cancel_appointment("9876543210", appointment_id=apt_id)

    # Second cancellation fails
    with pytest.raises(AppointmentAlreadyCancelledError):
        service.cancel_appointment("9876543210", appointment_id=apt_id)

# =============================================================================
# 9. Appointment Dashboard Listing View Tests
# =============================================================================
def test_get_appointments_masked_phone(db_session):
    service = AppointmentService(db_session)
    service.book_appointment("9876543210", "doc_001", "slot_101")

    appointments = service.get_appointments()
    assert len(appointments) == 1
    assert appointments[0]["phone_number_masked"] == "******3210"
    assert "9876543210" not in appointments[0]["phone_number_masked"]
    assert appointments[0]["doctor_name"] == "Dr. Priya Rao"
