from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Photo(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "photos"

    circle_id = Column(
        String(36), ForeignKey("circles.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    storage_key = Column(String(500), nullable=False)
    thumbnail_key = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(50), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    taken_at = Column(DateTime(timezone=True), nullable=True)
    location_lat = Column(Numeric(10, 8), nullable=True)
    location_lng = Column(Numeric(11, 8), nullable=True)
    location_name = Column(String(255), nullable=True)
    caption = Column(Text, nullable=True)
    exif_data = Column(JSONB, nullable=True)
    hash = Column(String(64), nullable=True, index=True)

    circle = relationship("Circle", back_populates="photos")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    stories = relationship("Story", back_populates="photo")
    tags = relationship(
        "PhotoTag", back_populates="photo", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_photos_circle_id", "circle_id"),
        Index("idx_photos_taken_at", "taken_at"),
        Index("idx_photos_uploaded_by", "uploaded_by"),
        Index("idx_photos_hash", "hash"),
    )


class PhotoTag(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "photo_tags"

    photo_id = Column(
        String(36), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False
    )
    circle_member_id = Column(
        String(36), ForeignKey("circle_members.id", ondelete="SET NULL"), nullable=True
    )
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    x_position = Column(Numeric(5, 4), nullable=True)
    y_position = Column(Numeric(5, 4), nullable=True)
    created_by = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    photo = relationship("Photo", back_populates="tags")
    circle_member = relationship("CircleMember", back_populates="photo_tags")
    tagged_user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("idx_photo_tags_photo_id", "photo_id"),
        Index("idx_photo_tags_circle_member_id", "circle_member_id"),
    )
