from typing import Optional
from pydantic import BaseModel, ConfigDict

class DoctorBase(BaseModel):
    name: str
    speciality: str
    bio: Optional[str] = None
    active: int = 1

class DoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    speciality: str
    bio: Optional[str] = None
    active: int = 1

class DoctorListResponse(BaseModel):
    doctors: list[DoctorResponse]
