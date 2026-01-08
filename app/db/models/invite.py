from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Invite(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invites"

    circle_id = Column(
        String(36), ForeignKey("circles.id", ondelete="CASCADE"), nullable=False
    )
    invite_code = Column(String(20), unique=True, nullable=False, index=True)
    invited_by = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_role = Column(String(20), default="contributor", nullable=False)
    assigned_label = Column(String(50), nullable=True)
    max_uses = Column(Integer, default=1, nullable=False)
    use_count = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    circle = relationship("Circle", back_populates="invites")
    inviter = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        Index("idx_invites_circle_id", "circle_id"),
        Index("idx_invites_invite_code", "invite_code"),
        Index("idx_invites_expires_at", "expires_at"),
    )
