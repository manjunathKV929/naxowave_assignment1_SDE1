from datetime import datetime, timezone
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from backend.app.models.doctor import Doctor
from backend.app.models.slot import Slot
from backend.app.models.appointment import Appointment
from backend.app.models.activity import ActivityEvent
from backend.app.schemas.common import (
    normalize_phone_number,
    mask_phone_number,
    ValidationError,
    DoctorNotFoundError,
    NoSlotsError,
    SlotUnavailableError,
    AppointmentNotFoundError,
    AppointmentAlreadyCancelledError,
)

def _get_utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class AppointmentService:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # Doctor Queries
    # -------------------------------------------------------------------------
    def get_doctors(self, active_only: bool = True) -> List[Doctor]:
        query = select(Doctor)
        if active_only:
            query = query.where(Doctor.active == 1)
        query = query.order_by(Doctor.name)
        return list(self.db.scalars(query).all())

    def get_doctor_by_id(self, doctor_id: str) -> Doctor:
        if not doctor_id:
            raise ValidationError("Doctor ID is required.")
        doctor = self.db.scalar(select(Doctor).where(Doctor.id == doctor_id))
        if not doctor:
            raise DoctorNotFoundError(f"Doctor with ID '{doctor_id}' does not exist.")
        return doctor

    # -------------------------------------------------------------------------
    # Availability Queries
    # -------------------------------------------------------------------------
    def check_availability(
        self,
        doctor_id: Optional[str] = None,
        speciality: Optional[str] = None,
        date_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query available slots filtered by doctor, speciality, and/or date.
        Returns a list of structured availability payloads.
        """
        query = select(Doctor).where(Doctor.active == 1)

        if doctor_id:
            query = query.where(Doctor.id == doctor_id)
        elif speciality:
            query = query.where(Doctor.speciality.ilike(f"%{speciality.strip()}%"))

        doctors = list(self.db.scalars(query).all())
        if doctor_id and not doctors:
            raise DoctorNotFoundError(f"Doctor '{doctor_id}' not found.")

        results = []
        for doc in doctors:
            slot_query = (
                select(Slot)
                .where(Slot.doctor_id == doc.id)
                .where(Slot.status == "available")
            )
            if date_str:
                slot_query = slot_query.where(Slot.slot_date == date_str.strip())
            slot_query = slot_query.order_by(Slot.slot_date, Slot.slot_time)

            slots = list(self.db.scalars(slot_query).all())
            if not slots:
                continue

            # Group slots by date
            slots_by_date: Dict[str, List[Dict[str, str]]] = {}
            for s in slots:
                slots_by_date.setdefault(s.slot_date, []).append({
                    "id": s.id,
                    "time": s.slot_time
                })

            for d, slist in slots_by_date.items():
                results.append({
                    "success": True,
                    "doctor_id": doc.id,
                    "doctor_name": doc.name,
                    "speciality": doc.speciality,
                    "date": d,
                    "slots": slist
                })

        return results

    # -------------------------------------------------------------------------
    # Booking Transaction
    # -------------------------------------------------------------------------
    def book_appointment(self, phone_number: str, doctor_id: str, slot_id: str) -> Dict[str, Any]:
        """Atomically book a doctor's appointment.
        Validates phone number, doctor existence, slot availability, and prevents double bookings.
        """
        normalized_phone = normalize_phone_number(phone_number)

        try:
            # 1. Verify doctor exists and is active
            doctor = self.db.scalar(select(Doctor).where(Doctor.id == doctor_id, Doctor.active == 1))
            if not doctor:
                raise DoctorNotFoundError(f"Doctor with ID '{doctor_id}' does not exist or is inactive.")

            # 2. Verify slot exists and belongs to doctor
            slot = self.db.scalar(select(Slot).where(Slot.id == slot_id, Slot.doctor_id == doctor_id))
            if not slot:
                raise SlotUnavailableError(f"Slot '{slot_id}' not found for doctor '{doctor.name}'.")

            # 3. Check slot availability
            if slot.status != "available":
                raise SlotUnavailableError(
                    f"The selected slot on {slot.slot_date} at {slot.slot_time} is no longer available (current status: {slot.status})."
                )

            # 4. Check for duplicate booking for this phone number at the same slot
            existing_booking = self.db.scalar(
                select(Appointment).where(
                    Appointment.phone_number == normalized_phone,
                    Appointment.slot_id == slot_id,
                    Appointment.status == "confirmed"
                )
            )
            if existing_booking:
                raise SlotUnavailableError("An active appointment for this slot already exists for this phone number.")

            now = _get_utc_now_iso()
            appointment_id = f"apt_{uuid.uuid4().hex[:8]}"

            # 5. Mark slot as booked
            slot.status = "booked"

            # 6. Create appointment
            appointment = Appointment(
                id=appointment_id,
                phone_number=normalized_phone,
                doctor_id=doctor.id,
                slot_id=slot.id,
                status="confirmed",
                created_at=now,
                updated_at=now
            )
            self.db.add(appointment)

            # 7. Create activity event
            event = ActivityEvent(
                id=f"act_{uuid.uuid4().hex[:8]}",
                event_type="appointment.created",
                message=f"Appointment booked for {mask_phone_number(normalized_phone)} with {doctor.name} on {slot.slot_date} at {slot.slot_time}.",
                appointment_id=appointment.id,
                created_at=now
            )
            self.db.add(event)

            # Commit the atomic transaction
            self.db.commit()
            self.db.refresh(appointment)

            return {
                "success": True,
                "appointment_id": appointment.id,
                "status": "confirmed",
                "doctor_id": doctor.id,
                "doctor_name": doctor.name,
                "speciality": doctor.speciality,
                "slot_id": slot.id,
                "date": slot.slot_date,
                "time": slot.slot_time,
                "phone_number_masked": mask_phone_number(normalized_phone)
            }
        except Exception:
            self.db.rollback()
            raise

    # -------------------------------------------------------------------------
    # Cancellation Transaction
    # -------------------------------------------------------------------------
    def cancel_appointment(self, phone_number: str, appointment_id: Optional[str] = None) -> Dict[str, Any]:
        """Atomically cancel an appointment located by confirmed phone number.
        Returns the slot to 'available' and records an activity event.
        """
        normalized_phone = normalize_phone_number(phone_number)

        try:
            # Query active appointment by phone
            query = (
                select(Appointment)
                .where(Appointment.phone_number == normalized_phone)
                .order_by(desc(Appointment.created_at))
            )
            if appointment_id:
                query = query.where(Appointment.id == appointment_id)

            appointments = list(self.db.scalars(query).all())

            # Check if any appointment exists at all for this phone
            if not appointments:
                # If specific ID was requested, check if it exists in another status or under another number
                if appointment_id:
                    any_apt = self.db.scalar(select(Appointment).where(Appointment.id == appointment_id))
                    if any_apt and any_apt.status == "cancelled":
                        raise AppointmentAlreadyCancelledError("Appointment has already been cancelled.")
                raise AppointmentNotFoundError(
                    f"No active appointment found for phone ending in {mask_phone_number(normalized_phone)}."
                )

            # Find the first confirmed appointment to cancel
            target_appointment = next((a for a in appointments if a.status == "confirmed"), None)
            if not target_appointment:
                raise AppointmentAlreadyCancelledError(
                    "All appointments for this phone number have already been cancelled."
                )

            now = _get_utc_now_iso()

            # 1. Update appointment status
            target_appointment.status = "cancelled"
            target_appointment.updated_at = now

            # 2. Release slot back to 'available'
            slot = self.db.scalar(select(Slot).where(Slot.id == target_appointment.slot_id))
            doctor = self.db.scalar(select(Doctor).where(Doctor.id == target_appointment.doctor_id))
            doctor_name = doctor.name if doctor else "Doctor"

            if slot:
                slot.status = "available"

            # 3. Create activity event
            event = ActivityEvent(
                id=f"act_{uuid.uuid4().hex[:8]}",
                event_type="appointment.cancelled",
                message=f"Appointment cancelled for {mask_phone_number(normalized_phone)} with {doctor_name}.",
                appointment_id=target_appointment.id,
                created_at=now
            )
            self.db.add(event)

            self.db.commit()
            self.db.refresh(target_appointment)

            return {
                "success": True,
                "appointment_id": target_appointment.id,
                "status": "cancelled",
                "phone_number_masked": mask_phone_number(normalized_phone),
                "message": f"Appointment with {doctor_name} has been cancelled successfully."
            }
        except Exception:
            self.db.rollback()
            raise

    # -------------------------------------------------------------------------
    # Appointment Listing & Activity Queries
    # -------------------------------------------------------------------------
    def get_appointments(
        self,
        phone_number: Optional[str] = None,
        status: Optional[str] = None,
        date_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve appointments with doctor and slot details. Full phone numbers are masked."""
        query = select(Appointment).order_by(desc(Appointment.created_at))

        if phone_number:
            normalized_phone = normalize_phone_number(phone_number)
            query = query.where(Appointment.phone_number == normalized_phone)
        if status:
            query = query.where(Appointment.status == status)

        appointments = list(self.db.scalars(query).all())

        results = []
        for apt in appointments:
            slot = self.db.scalar(select(Slot).where(Slot.id == apt.slot_id))
            doctor = self.db.scalar(select(Doctor).where(Doctor.id == apt.doctor_id))

            if date_str and slot and slot.slot_date != date_str:
                continue

            results.append({
                "id": apt.id,
                "phone_number_masked": mask_phone_number(apt.phone_number),
                "doctor_id": apt.doctor_id,
                "doctor_name": doctor.name if doctor else "Unknown",
                "speciality": doctor.speciality if doctor else "Unknown",
                "slot_id": apt.slot_id,
                "slot_date": slot.slot_date if slot else "Unknown",
                "slot_time": slot.slot_time if slot else "Unknown",
                "status": apt.status,
                "created_at": apt.created_at,
                "updated_at": apt.updated_at
            })

        return results

    def get_activity_events(self, limit: int = 20) -> List[ActivityEvent]:
        query = select(ActivityEvent).order_by(desc(ActivityEvent.created_at)).limit(limit)
        return list(self.db.scalars(query).all())
