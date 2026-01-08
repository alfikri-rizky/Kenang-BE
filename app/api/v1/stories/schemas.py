from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateStoryRequest(BaseModel):
    circle_id: str = Field(..., description="ID lingkaran tempat cerita dibuat")
    audio_storage_key: str = Field(..., description="Storage key audio yang sudah diupload ke S3")
    photo_id: Optional[str] = Field(None, description="ID foto yang terkait dengan cerita (opsional)")
    prompt_used: Optional[str] = Field(None, max_length=500, description="Prompt yang digunakan untuk memandu rekaman")
    audio_duration_seconds: Optional[int] = Field(None, ge=1, le=600, description="Durasi audio dalam detik")
    language: str = Field("id", max_length=10, description="Kode bahasa untuk transkripsi (default: id)")


class UpdateTranscriptRequest(BaseModel):
    transcript_edited: str = Field(..., min_length=1, description="Transkrip yang sudah diedit")


class RecorderInfo(BaseModel):
    id: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class PhotoInfo(BaseModel):
    id: str
    storage_key: str
    thumbnail_key: Optional[str] = None
    caption: Optional[str] = None

    class Config:
        from_attributes = True


class StoryResponse(BaseModel):
    id: str
    circle_id: str
    photo_id: Optional[str] = None
    recorded_by: Optional[str] = None
    audio_url: str
    audio_storage_key: str
    audio_duration_seconds: Optional[int] = None
    transcript_original: Optional[str] = None
    transcript_edited: Optional[str] = None
    transcription_status: str
    transcription_error: Optional[str] = None
    prompt_used: Optional[str] = None
    language: str
    is_published: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    recorder: Optional[RecorderInfo] = None
    photo: Optional[PhotoInfo] = None

    class Config:
        from_attributes = True


class StoryListResponse(BaseModel):
    stories: list[StoryResponse]
    total: int
    skip: int
    limit: int


class TranscriptionStatusResponse(BaseModel):
    status: str = Field(..., description="Status transkripsi: pending, processing, completed, failed")
    error: Optional[str] = Field(None, description="Pesan error jika status failed")
    has_transcript: bool = Field(..., description="Apakah sudah ada transkrip")
