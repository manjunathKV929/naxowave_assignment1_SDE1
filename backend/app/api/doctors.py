from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.appointment_service import AppointmentService
from backend.app.schemas.doctor import DoctorListResponse, DoctorResponse
from backend.app.schemas.slot import AvailabilityResponse

router = APIRouter(prefix="/api", tags=["doctors"])

@router.get("/doctors", response_model=DoctorListResponse)
def list_doctors(
    active_only: bool = Query(True, description="Filter only active doctors"),
    db: Session = Depends(get_db)
):
    """Retrieve list of registered doctors."""
    service = AppointmentService(db)
    doctors = service.get_doctors(active_only=active_only)
    return {"doctors": [DoctorResponse.model_validate(doc) for doc in doctors]}

@router.get("/doctors/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id: str,
    db: Session = Depends(get_db)
):
    """Get single doctor details by ID."""
    service = AppointmentService(db)
    doctor = service.get_doctor_by_id(doctor_id)
    return DoctorResponse.model_validate(doctor)

@router.get("/doctors/{doctor_id}/availability")
def get_doctor_availability(
    doctor_id: str,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """Get available appointment slots for a specific doctor on a given date."""
    service = AppointmentService(db)
    results = service.check_availability(doctor_id=doctor_id, date_str=date)
    if not results:
        doc = service.get_doctor_by_id(doctor_id)
        return {
            "success": True,
            "doctor_id": doc.id,
            "doctor_name": doc.name,
            "speciality": doc.speciality,
            "date": date or "",
            "slots": []
        }
    res = dict(results[0])
    res["success"] = True
    return res

@router.get("/availability")
def search_availability(
    doctor_id: Optional[str] = Query(None, description="Doctor ID"),
    speciality: Optional[str] = Query(None, description="Medical speciality"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """Search available slots across doctors, specialities, or dates."""
    service = AppointmentService(db)
    results = service.check_availability(
        doctor_id=doctor_id,
        speciality=speciality,
        date_str=date
    )
    return {"success": True, "availability": results}
