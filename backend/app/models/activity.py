from sqlalchemy import Column, Index, String, Text
from backend.app.db.session import Base

class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(String, primary_key=True, index=True)
    event_type = Column(String, nullable=False)  # 'appointment.created', 'appointment.cancelled', etc.
    message = Column(String, nullable=False)
    appointment_id = Column(String, nullable=True)
    created_at = Column(String, nullable=False)  # ISO 8601 UTC

    __table_args__ = (
        Index("idx_activity_created", "created_at"),
    )
