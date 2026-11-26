"""Database seeder for CareFlow AI.
Seeds doctors, slots across multiple dates, and initializes tables.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import engine, Base, SessionLocal
from backend.app.models.doctor import Doctor
from backend.app.models.slot import Slot
from backend.app.models.appointment import Appointment
from backend.app.models.activity import ActivityEvent

DOCTORS_SEED_DATA = [
    {
        "id": "doc_001",
        "name": "Dr. Priya Rao",
        "speciality": "Cardiology",
        "bio": "Senior Consultant Cardiologist specializing in preventive cardiology and heart rhythm management.",
        "active": 1,
    },
    {
        "id": "doc_002",
        "name": "Dr. Marcus Vance",
        "speciality": "Dermatology",
        "bio": "Board-certified Dermatologist with expertise in clinical dermatology, acne, and skin health.",
        "active": 1,
    },
    {
        "id": "doc_003",
        "name": "Dr. Sarah Chen",
        "speciality": "Pediatrics",
        "bio": "Experienced Pediatrician dedicated to childhood development, immunization, and adolescent health.",
        "active": 1,
    },
    {
        "id": "doc_004",
        "name": "Dr. David Kim",
        "speciality": "Orthopedics",
        "bio": "Orthopedic surgeon specializing in sports medicine, joint restoration, and musculoskeletal health.",
        "active": 1,
    },
    {
        "id": "doc_005",
        "name": "Dr. Elena Rostova",
        "speciality": "Neurology",
        "bio": "Neurologist focused on migraine relief, sleep medicine, and neurological rehabilitation.",
        "active": 1,
    },
    {
        "id": "doc_006",
        "name": "Dr. Rajesh Sharma",
        "speciality": "General Medicine",
        "bio": "Primary care physician focusing on holistic adult wellness and chronic disease prevention.",
        "active": 1,
    },
    {
        "id": "doc_007",
        "name": "Dr. Maya Patel",
        "speciality": "Endocrinology",
        "bio": "Specialist in hormone balance, diabetes management, and metabolic health.",
        "active": 1,
    },
]

SLOT_TIMES = ["09:00", "10:30", "11:30", "14:00", "15:30", "16:30"]

def init_db():
    """Create all tables in SQLite database."""
    Base.metadata.create_all(bind=engine)

def seed_database(db: Session = None, reset: bool = False):
    """Seed doctors and slots. If reset=True, drop and recreate tables first."""
    if reset:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    else:
        init_db()

    session_created = False
    if db is None:
        db = SessionLocal()
        session_created = True

    try:
        # Seed Doctors
        for doc_data in DOCTORS_SEED_DATA:
            existing_doc = db.scalar(select(Doctor).where(Doctor.id == doc_data["id"]))
            if not existing_doc:
                doctor = Doctor(**doc_data)
                db.add(doctor)

        db.flush()

        # Generate target dates: today, tomorrow, +2 days, +3 days, plus fixed reference dates
        now = datetime.now(timezone.utc)
        target_dates = set()
        for offset in [0, 1, 2, 3]:
            target_dates.add((now + timedelta(days=offset)).strftime("%Y-%m-%d"))
        
        # Include reference dates for tests/reproducibility
        target_dates.update(["2026-11-24", "2026-11-25", "2026-11-26"])

        # Seed Slots for all doctors
        all_doctors = list(db.scalars(select(Doctor)).all())
        created_slots_count = 0

        for doc in all_doctors:
            for d in sorted(target_dates):
                for t in SLOT_TIMES:
                    slot_id = f"slot_{doc.id}_{d.replace('-', '')}_{t.replace(':', '')}"
                    existing_slot = db.scalar(select(Slot).where(Slot.id == slot_id))
                    if not existing_slot:
                        slot = Slot(
                            id=slot_id,
                            doctor_id=doc.id,
                            slot_date=d,
                            slot_time=t,
                            status="available"
                        )
                        db.add(slot)
                        created_slots_count += 1

        # Seed an initial activity event if none exists
        existing_event = db.scalar(select(ActivityEvent).limit(1))
        if not existing_event:
            event = ActivityEvent(
                id="act_init_001",
                event_type="system.initialized",
                message="CareFlow AI database initialized and verified.",
                appointment_id=None,
                created_at=now.isoformat()
            )
            db.add(event)

        db.commit()
        print(f"Database seeded successfully: {len(all_doctors)} doctors, {created_slots_count} new slots.")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        if session_created:
            db.close()

if __name__ == "__main__":
    seed_database(reset=False)
