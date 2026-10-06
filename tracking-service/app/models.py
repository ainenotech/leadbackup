from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from .database import Base


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id = Column(Integer, primary_key=True, index=True)

    token = Column(String(255), nullable=False, index=True)

    event_type = Column(String(50), nullable=False, index=True)

    target_url = Column(Text, nullable=True)

    ip_address = Column(String(100), nullable=True)

    user_agent = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )