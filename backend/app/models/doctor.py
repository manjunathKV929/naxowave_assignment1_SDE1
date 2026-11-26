from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.db.session import Base

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    speciality = Column(String, nullable=False, index=True)
    bio = Column(Text, nullable=True)
    active = Column(Integer, nullable=False, default=1)

    slots = relationship("Slot", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")
