from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator
from backend.app.schemas.common import normalize_phone_number, mask_phone_number

class AppointmentCreateRequest(BaseModel):
    phone_number: str
    doctor_id: str
    slot_id: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)

class AppointmentCancelRequest(BaseModel):
    phone_number: str
    appointment_id: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)

class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone_number: str  # Note: displayed masked in dashboard APIs
    doctor_id: str
    doctor_name: Optional[str] = None
    speciality: Optional[str] = None
    slot_id: str
    slot_date: Optional[str] = None
    slot_time: Optional[str] = None
    status: str
    created_at: str
    updated_at: str

class AppointmentDashboardView(BaseModel):
    id: str
    phone_number_masked: str
    doctor_id: str
    doctor_name: str
    speciality: str
    slot_id: str
    slot_date: str
    slot_time: str
    status: str
    created_at: str
    updated_at: str

class BookingResult(BaseModel):
    success: bool
    appointment_id: str
    status: str
    doctor_name: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    phone_number_masked: Optional[str] = None

class CancellationResult(BaseModel):
    success: bool
    appointment_id: str
    status: str
    message: Optional[str] = None
