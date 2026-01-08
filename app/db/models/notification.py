from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class NotificationType(str, Enum):
    NEW_STORY = "new_story"
    NEW_MEMBER = "new_member"
    INVITE_ACCEPTED = "invite_accepted"
    TIME_CAPSULE_DELIVERED = "time_capsule_delivered"
    STORY_TRANSCRIBED = "story_transcribed"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    WEEKLY_REMINDER = "weekly_reminder"


class DevicePlatform(str, Enum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=True)
    body = Column(Text, nullable=True)
    data = Column(JSONB, nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_type", "type"),
        Index("idx_notifications_read_at", "read_at"),
        Index("idx_notifications_created_at", "created_at"),
    )


class DeviceToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "device_tokens"

    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token = Column(String(500), nullable=False)
    platform = Column(String(20), nullable=False)
    device_id = Column(String(255), nullable=True)
    is_active = Column(String(5), default="true", nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="device_tokens")

    __table_args__ = (
        Index("idx_device_tokens_user_id", "user_id"),
        Index("idx_device_tokens_token", "token"),
        Index("idx_device_tokens_platform", "platform"),
    )
