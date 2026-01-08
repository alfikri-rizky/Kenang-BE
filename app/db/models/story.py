from enum import Enum

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class TranscriptionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Story(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "stories"

    circle_id = Column(
        String(36), ForeignKey("circles.id", ondelete="CASCADE"), nullable=False
    )
    photo_id = Column(
        String(36), ForeignKey("photos.id", ondelete="SET NULL"), nullable=True
    )
    recorded_by = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    audio_url = Column(String(500), nullable=True)
    audio_storage_key = Column(String(500), nullable=True)
    audio_duration_seconds = Column(Integer, nullable=True)
    transcript_original = Column(Text, nullable=True)
    transcript_edited = Column(Text, nullable=True)
    transcription_status = Column(
        String(20), default=TranscriptionStatus.PENDING.value, nullable=False
    )
    transcription_error = Column(Text, nullable=True)
    prompt_used = Column(Text, nullable=True)
    language = Column(String(10), default="id", nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)

    circle = relationship("Circle", back_populates="stories")
    photo = relationship("Photo", back_populates="stories")
    recorder = relationship("User", foreign_keys=[recorded_by])

    __table_args__ = (
        Index("idx_stories_circle_id", "circle_id"),
        Index("idx_stories_photo_id", "photo_id"),
        Index("idx_stories_created_at", "created_at"),
        Index("idx_stories_recorded_by", "recorded_by"),
    )
