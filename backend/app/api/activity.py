from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.appointment_service import AppointmentService
from backend.app.schemas.activity import ActivityEventResponse

router = APIRouter(prefix="/api/activity", tags=["activity"])

@router.get("")
def get_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Max number of activity events to return"),
    db: Session = Depends(get_db)
):
    """Get list of recent system and appointment activity events."""
    service = AppointmentService(db)
    events = service.get_activity_events(limit=limit)
    return {
        "events": [ActivityEventResponse.model_validate(e) for e in events]
    }
