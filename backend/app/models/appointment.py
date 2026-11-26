from sqlalchemy import Column, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, index=True)
    phone_number = Column(String, nullable=False)
    doctor_id = Column(String, ForeignKey("doctors.id"), nullable=False)
    slot_id = Column(String, ForeignKey("slots.id"), nullable=False)
    status = Column(String, nullable=False, default="confirmed")  # 'confirmed', 'cancelled'
    created_at = Column(String, nullable=False)  # ISO 8601 UTC
    updated_at = Column(String, nullable=False)  # ISO 8601 UTC

    doctor = relationship("Doctor", back_populates="appointments")
    slot = relationship("Slot", back_populates="appointments")

    __table_args__ = (
        Index("idx_appointments_phone", "phone_number"),
        Index("idx_appointments_status", "status"),
    )
