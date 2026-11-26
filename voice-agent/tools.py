"""CareFlow AI — Voice Agent Function Tools.
Strictly-typed schemas and execution logic connecting LLM to AppointmentService.
"""
from typing import Optional, Dict, Any
from loguru import logger

from backend.app.db.session import SessionLocal
from backend.app.services.appointment_service import AppointmentService
from backend.app.schemas.common import normalize_phone_number, mask_phone_number, CareFlowException
from pipecat.adapters.llm.schemas.function_schema import FunctionSchema

# =============================================================================
# Tool Definitions (FunctionSchema)
# =============================================================================

CHECK_AVAILABILITY_SCHEMA = FunctionSchema(
    name="check_doctor_availability",
    description="Check real-time doctor availability and available appointment slots by doctor ID, medical speciality, or date. Never invent slots; only return real clinic availability.",
    properties={
        "doctor_id": {
            "type": "string",
            "description": "Optional unique ID of the doctor (e.g. 'doc_001')."
        },
        "speciality": {
            "type": "string",
            "description": "Optional medical speciality (e.g. 'Cardiology', 'Dermatology', 'Pediatrics')."
        },
        "date": {
            "type": "string",
            "description": "Optional date in YYYY-MM-DD format. If omitted, returns upcoming available dates."
        }
    },
    required=[]
)

BOOK_APPOINTMENT_SCHEMA = FunctionSchema(
    name="book_appointment",
    description="Book a confirmed doctor appointment. MUST ONLY be called AFTER the caller has verbally confirmed their phone number digit-by-digit.",
    properties={
        "phone_number": {
            "type": "string",
            "description": "The caller's 10-digit phone number, verbally verified with the caller."
        },
        "doctor_id": {
            "type": "string",
            "description": "The doctor ID chosen by the caller (e.g. 'doc_001')."
        },
        "slot_id": {
            "type": "string",
            "description": "The exact slot ID chosen by the caller (e.g. 'slot_doc_001_...')."
        }
    },
    required=["phone_number", "doctor_id", "slot_id"]
)

CANCEL_APPOINTMENT_SCHEMA = FunctionSchema(
    name="cancel_appointment",
    description="Cancel an existing doctor appointment for a caller. MUST ONLY be called AFTER the caller has verbally confirmed their phone number.",
    properties={
        "phone_number": {
            "type": "string",
            "description": "The caller's 10-digit phone number used for the booking, verbally verified."
        },
        "appointment_id": {
            "type": "string",
            "description": "Optional specific appointment ID if provided by the caller."
        }
    },
    required=["phone_number"]
)

ALL_VOICE_TOOLS = [
    CHECK_AVAILABILITY_SCHEMA,
    BOOK_APPOINTMENT_SCHEMA,
    CANCEL_APPOINTMENT_SCHEMA
]

# =============================================================================
# Tool Execution Handlers (Service Layer Boundary)
# =============================================================================

def execute_check_availability(
    doctor_id: Optional[str] = None,
    speciality: Optional[str] = None,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """Execute availability lookup through AppointmentService."""
    db = SessionLocal()
    try:
        service = AppointmentService(db)
        results = service.check_availability(
            doctor_id=doctor_id,
            speciality=speciality,
            date_str=date
        )
        if not results:
            return {
                "success": True,
                "message": "No available slots found matching the requested criteria.",
                "availability": []
            }
        return {
            "success": True,
            "availability": results
        }
    except CareFlowException as e:
        return {"success": False, "error": {"code": e.code, "message": e.message}}
    except Exception as e:
        logger.error(f"Error in execute_check_availability: {e}")
        return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": "Failed to check doctor availability."}}
    finally:
        db.close()


def execute_book_appointment(
    phone_number: str,
    doctor_id: str,
    slot_id: str,
    phone_confirmed: bool = True
) -> Dict[str, Any]:
    """Execute atomic booking through AppointmentService."""
    if not phone_confirmed:
        return {
            "success": False,
            "error": {
                "code": "CONFIRMATION_REQUIRED",
                "message": "Caller phone number must be verbally repeated and confirmed before booking."
            }
        }

    db = SessionLocal()
    try:
        service = AppointmentService(db)
        result = service.book_appointment(
            phone_number=phone_number,
            doctor_id=doctor_id,
            slot_id=slot_id
        )
        return result
    except CareFlowException as e:
        return {"success": False, "error": {"code": e.code, "message": e.message}}
    except Exception as e:
        logger.error(f"Error in execute_book_appointment: {e}")
        return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An error occurred while booking the appointment."}}
    finally:
        db.close()


def execute_cancel_appointment(
    phone_number: str,
    appointment_id: Optional[str] = None,
    phone_confirmed: bool = True
) -> Dict[str, Any]:
    """Execute atomic cancellation through AppointmentService."""
    if not phone_confirmed:
        return {
            "success": False,
            "error": {
                "code": "CONFIRMATION_REQUIRED",
                "message": "Caller phone number must be verbally repeated and confirmed before cancellation."
            }
        }

    db = SessionLocal()
    try:
        service = AppointmentService(db)
        result = service.cancel_appointment(
            phone_number=phone_number,
            appointment_id=appointment_id
        )
        return result
    except CareFlowException as e:
        return {"success": False, "error": {"code": e.code, "message": e.message}}
    except Exception as e:
        logger.error(f"Error in execute_cancel_appointment: {e}")
        return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An error occurred while cancelling the appointment."}}
    finally:
        db.close()
