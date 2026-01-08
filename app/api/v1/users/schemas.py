from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserProfileResponse(BaseModel):
    id: str
    phone_number: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    language: str = "id"
    timezone: str = "Asia/Jakarta"
    subscription_tier: str = "free"
    subscription_expires_at: Optional[datetime] = None
    created_at: datetime
    last_active_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    language: Optional[str] = Field(None, pattern=r"^(id|en|jv|su)$")
    timezone: Optional[str] = Field(None, max_length=50)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Nama tidak boleh kosong")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_timezones = [
                "Asia/Jakarta",
                "Asia/Makassar",
                "Asia/Jayapura",
                "UTC",
            ]
            if v not in valid_timezones:
                raise ValueError(
                    f"Zona waktu tidak valid. Pilih: {', '.join(valid_timezones)}"
                )
        return v


class UpdateProfileResponse(BaseModel):
    message: str = "Profil berhasil diperbarui"
    user: UserProfileResponse


class DeleteAccountRequest(BaseModel):
    confirm: bool = Field(
        ...,
        description="Konfirmasi penghapusan akun. Harus bernilai true.",
    )

    @field_validator("confirm")
    @classmethod
    def validate_confirm(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Anda harus mengkonfirmasi penghapusan akun dengan mengirim confirm=true"
            )
        return v


class DeleteAccountResponse(BaseModel):
    message: str = "Akun berhasil dihapus. Terima kasih telah menggunakan Kenang."


class UserStatsResponse(BaseModel):
    total_circles: int = 0
    total_photos: int = 0
    total_stories: int = 0
    circles_remaining: int = 0
    photos_remaining: int = 0
    stories_remaining: int = 0
