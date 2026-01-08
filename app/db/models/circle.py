from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class CircleType(str, Enum):
    KELUARGA = "keluarga"
    PASANGAN = "pasangan"
    SAHABAT = "sahabat"
    REKAN_KERJA = "rekan_kerja"
    KOMUNITAS = "komunitas"
    MENTOR = "mentor"
    PRIBADI = "pribadi"


class CirclePrivacy(str, Enum):
    PRIVATE = "private"
    MEMBERS_ONLY = "members_only"
    LINK_ACCESS = "link_access"


class MemberRole(str, Enum):
    ADMIN = "admin"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class Circle(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "circles"

    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=True)
    cover_photo_url = Column(String(500), nullable=True)
    privacy = Column(
        String(20), default=CirclePrivacy.MEMBERS_ONLY.value, nullable=False
    )
    invite_code = Column(String(20), unique=True, nullable=True, index=True)
    invite_code_expires_at = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSONB, default=dict, nullable=False)
    created_by = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    creator = relationship(
        "User", back_populates="created_circles", foreign_keys=[created_by]
    )
    memberships = relationship(
        "CircleMembership", back_populates="circle", cascade="all, delete-orphan"
    )
    members = relationship(
        "CircleMember", back_populates="circle", cascade="all, delete-orphan"
    )
    photos = relationship(
        "Photo", back_populates="circle", cascade="all, delete-orphan"
    )
    stories = relationship(
        "Story", back_populates="circle", cascade="all, delete-orphan"
    )
    invites = relationship(
        "Invite", back_populates="circle", cascade="all, delete-orphan"
    )
    time_capsules = relationship(
        "TimeCapsule", back_populates="circle", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_circles_type", "type"),
        Index("idx_circles_invite_code", "invite_code"),
        Index("idx_circles_created_by", "created_by"),
    )


class CircleMembership(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "circle_memberships"

    circle_id = Column(
        String(36), ForeignKey("circles.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(20), default=MemberRole.CONTRIBUTOR.value, nullable=False)
    custom_label = Column(String(50), nullable=True)
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    invited_by = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    circle = relationship("Circle", back_populates="memberships")
    user = relationship(
        "User", back_populates="circle_memberships", foreign_keys=[user_id]
    )
    inviter = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        Index("idx_circle_memberships_user_id", "user_id"),
        Index("idx_circle_memberships_circle_id", "circle_id"),
        Index(
            "uq_circle_memberships_circle_user",
            "circle_id",
            "user_id",
            unique=True,
        ),
    )


class CircleMember(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "circle_members"

    circle_id = Column(
        String(36), ForeignKey("circles.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    custom_label = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    linked_user_id = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    circle = relationship("Circle", back_populates="members")
    linked_user = relationship("User", foreign_keys=[linked_user_id])
    creator = relationship("User", foreign_keys=[created_by])
    photo_tags = relationship(
        "PhotoTag", back_populates="circle_member", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_circle_members_circle_id", "circle_id"),
        Index("idx_circle_members_linked_user_id", "linked_user_id"),
    )
