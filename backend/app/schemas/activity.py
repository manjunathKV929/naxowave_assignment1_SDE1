from typing import Optional
from pydantic import BaseModel, ConfigDict

class ActivityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    message: str
    appointment_id: Optional[str] = None
    created_at: str
