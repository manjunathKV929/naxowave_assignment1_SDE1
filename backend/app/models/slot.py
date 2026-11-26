from sqlalchemy import Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

class Slot(Base):
    __tablename__ = "slots"

    id = Column(String, primary_key=True, index=True)
    doctor_id = Column(String, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    slot_date = Column(String, nullable=False)  # Format: YYYY-MM-DD
    slot_time = Column(String, nullable=False)  # Format: HH:MM
    status = Column(String, nullable=False, default="available")  # 'available', 'booked', 'blocked'

    doctor = relationship("Doctor", back_populates="slots")
    appointments = relationship("Appointment", back_populates="slot")

    __table_args__ = (
        UniqueConstraint("doctor_id", "slot_date", "slot_time", name="uq_doctor_date_time"),
        Index("idx_slots_doctor_date", "doctor_id", "slot_date"),
    )
