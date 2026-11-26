from typing import Optional
from pydantic import BaseModel, ConfigDict

class SlotBase(BaseModel):
    doctor_id: str
    slot_date: str
    slot_time: str
    status: str = "available"

class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    doctor_id: str
    slot_date: str
    slot_time: str
    status: str

class AvailabilitySlot(BaseModel):
    id: str
    time: str

class AvailabilityResponse(BaseModel):
    success: bool = True
    doctor_id: str
    doctor_name: str
    speciality: str
    date: str
    slots: list[AvailabilitySlot]
