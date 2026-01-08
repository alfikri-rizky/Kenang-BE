from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class RecipientType(str, Enum):
    ALL_MEMBERS = "all_members"
    SPECIFIC_MEMBERS = "specific_members"


class TimeCapsuleStatus(str, Enum):
    SCHEDULED = "scheduled"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class TimeCapsule(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "time_capsules"

    circle_id = Column(
        String(36), ForeignKey("circles.id", ondelete="CASCADE"), nullable=False
    )
    created_by = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title = Column(String(200), nullable=True)
    message = Column(Text, nullable=True)
    attached_story_ids = Column(ARRAY(String(36)), nullable=True)
    attached_photo_ids = Column(ARRAY(String(36)), nullable=True)
    scheduled_delivery_at = Column(DateTime(timezone=True), nullable=False)
    recipient_type = Column(
        String(20), default=RecipientType.ALL_MEMBERS.value, nullable=False
    )
    recipient_user_ids = Column(ARRAY(String(36)), nullable=True)
    status = Column(String(20), default=TimeCapsuleStatus.SCHEDULED.value, nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    circle = relationship("Circle", back_populates="time_capsules")
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("idx_time_capsules_circle_id", "circle_id"),
        Index("idx_time_capsules_scheduled_delivery_at", "scheduled_delivery_at"),
        Index("idx_time_capsules_status", "status"),
    )
