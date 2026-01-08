from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UploadPhotoRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., pattern=r"^image/")
    circle_id: str


class UploadPhotoResponse(BaseModel):
    upload_url: str
    fields: dict
    storage_key: str
    expires_in: int


class ConfirmPhotoUploadRequest(BaseModel):
    storage_key: str
    circle_id: str
    caption: Optional[str] = Field(None, max_length=500)
    taken_at: Optional[datetime] = None


class PhotoResponse(BaseModel):
    id: str
    circle_id: str
    storage_key: str
    thumbnail_key: Optional[str] = None
    url: str
    thumbnail_url: Optional[str] = None
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    taken_at: Optional[datetime] = None
    caption: Optional[str] = None
    uploaded_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    photos: list[PhotoResponse]
    total: int


class UpdatePhotoRequest(BaseModel):
    caption: Optional[str] = Field(None, max_length=500)
    taken_at: Optional[datetime] = None


class UploadAudioRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., pattern=r"^audio/")
    circle_id: str
    photo_id: Optional[str] = None


class UploadAudioResponse(BaseModel):
    upload_url: str
    fields: dict
    storage_key: str
    expires_in: int
