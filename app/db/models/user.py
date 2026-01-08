from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class SubscriptionTier(str, Enum):
    FREE = "free"
    PERSONAL = "personal"
    PLUS = "plus"
    PREMIUM = "premium"


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    phone_verified = Column(Boolean, default=False, nullable=False)
    display_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    language = Column(String(10), default="id", nullable=False)
    timezone = Column(String(50), default="Asia/Jakarta", nullable=False)
    subscription_tier = Column(
        String(20), default=SubscriptionTier.FREE.value, nullable=False
    )
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    circle_memberships = relationship(
        "CircleMembership", back_populates="user", cascade="all, delete-orphan"
    )
    created_circles = relationship(
        "Circle", back_populates="creator", foreign_keys="Circle.created_by"
    )
    otp_codes = relationship(
        "OTPCode", back_populates="user", cascade="all, delete-orphan"
    )
    device_tokens = relationship(
        "DeviceToken", back_populates="user", cascade="all, delete-orphan"
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_users_phone_number", "phone_number"),)


class OTPCode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "otp_codes"

    phone_number = Column(String(20), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(String(2), default="0", nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    user = relationship("User", back_populates="otp_codes")

    __table_args__ = (
        Index("idx_otp_codes_phone_number", "phone_number"),
        Index("idx_otp_codes_expires_at", "expires_at"),
    )
