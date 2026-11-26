from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.services.appointment_service import AppointmentService
from backend.app.schemas.appointment import (
    AppointmentCreateRequest,
    AppointmentCancelRequest,
)
from backend.app.schemas.common import normalize_phone_number, ValidationError
from backend.app.models.appointment import Appointment

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

@router.get("")
def list_appointments(
    status: Optional[str] = Query(None, description="Filter by status: confirmed, cancelled"),
    date: Optional[str] = Query(None, description="Filter by slot date YYYY-MM-DD"),
    phone: Optional[str] = Query(None, description="Filter by phone number"),
    db: Session = Depends(get_db)
):
    """List appointments for dashboard. Caller phone numbers are always masked."""
    service = AppointmentService(db)
    appointments = service.get_appointments(
        phone_number=phone,
        status=status,
        date_str=date
    )
    return {"appointments": appointments}

@router.post("")
def book_appointment(
    payload: AppointmentCreateRequest,
    db: Session = Depends(get_db)
):
    """Book a new doctor appointment."""
    service = AppointmentService(db)
    result = service.book_appointment(
        phone_number=payload.phone_number,
        doctor_id=payload.doctor_id,
        slot_id=payload.slot_id
    )
    return {
        "success": True,
        "appointment": {
            "id": result["appointment_id"],
            "status": result["status"],
            "doctor_name": result["doctor_name"],
            "date": result["date"],
            "time": result["time"],
            "phone_number_masked": result["phone_number_masked"]
        }
    }

@router.post("/cancel")
def cancel_appointment_by_phone(
    payload: AppointmentCancelRequest,
    db: Session = Depends(get_db)
):
    """Cancel an appointment using the caller's confirmed phone number."""
    service = AppointmentService(db)
    result = service.cancel_appointment(
        phone_number=payload.phone_number,
        appointment_id=payload.appointment_id
    )
    return {
        "success": True,
        "appointment_id": result["appointment_id"],
        "status": result["status"],
        "message": result["message"]
    }

@router.post("/{appointment_id}/cancel")
def cancel_appointment_by_id(
    appointment_id: str,
    payload: Optional[Dict[str, Any]] = Body(None),
    db: Session = Depends(get_db)
):
    """Cancel a specific appointment by ID."""
    service = AppointmentService(db)
    phone_number = payload.get("phone_number") if payload else None

    # If phone_number is not provided in body, lookup the appointment to get its phone number
    if not phone_number:
        apt = db.scalar(select(Appointment).where(Appointment.id == appointment_id))
        if apt:
            phone_number = apt.phone_number
        else:
            phone_number = "0000000000"

    result = service.cancel_appointment(
        phone_number=phone_number,
        appointment_id=appointment_id
    )
    return {
        "success": True,
        "appointment_id": result["appointment_id"],
        "status": result["status"]
    }
