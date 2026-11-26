from typing import Generic, Optional, TypeVar
from pydantic import BaseModel
import re

T = TypeVar("T")

class ErrorDetail(BaseModel):
    code: str
    message: str

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None

class CareFlowException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

class ValidationError(CareFlowException):
    def __init__(self, message: str):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422)

class DoctorNotFoundError(CareFlowException):
    def __init__(self, message: str = "Doctor not found"):
        super().__init__(code="DOCTOR_NOT_FOUND", message=message, status_code=404)

class NoSlotsError(CareFlowException):
    def __init__(self, message: str = "No available slots found for the requested criteria"):
        super().__init__(code="NO_SLOTS", message=message, status_code=404)

class SlotUnavailableError(CareFlowException):
    def __init__(self, message: str = "The selected slot is no longer available"):
        super().__init__(code="SLOT_UNAVAILABLE", message=message, status_code=409)

class AppointmentNotFoundError(CareFlowException):
    def __init__(self, message: str = "No confirmed appointment found for the provided information"):
        super().__init__(code="APPOINTMENT_NOT_FOUND", message=message, status_code=404)

class AppointmentAlreadyCancelledError(CareFlowException):
    def __init__(self, message: str = "Appointment has already been cancelled"):
        super().__init__(code="APPOINTMENT_ALREADY_CANCELLED", message=message, status_code=409)

def normalize_phone_number(phone: str) -> str:
    """Normalize phone string by stripping non-digit characters.
    Validates that normalized string contains 7-15 digits.
    """
    if not phone or not isinstance(phone, str):
        raise ValidationError("Phone number is required.")
    
    digits_only = re.sub(r"\D", "", phone)
    if len(digits_only) < 7 or len(digits_only) > 15:
        raise ValidationError(f"Invalid phone number '{phone}'. Must contain between 7 and 15 digits.")
    
    return digits_only

def mask_phone_number(phone: str) -> str:
    """Mask phone number for safe display (e.g. '******3210')."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) <= 4:
        return "****"
    return "*" * (len(digits) - 4) + digits[-4:]
