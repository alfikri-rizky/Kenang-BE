import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RequestOTPRequest(BaseModel):
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=20,
        examples=["+6281234567890"],
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("0"):
            v = "+62" + v[1:]
        elif v.startswith("62"):
            v = "+" + v
        elif not v.startswith("+"):
            v = "+62" + v

        pattern = r"^\+62[0-9]{8,13}$"
        if not re.match(pattern, v):
            raise ValueError(
                "Nomor telepon tidak valid. Gunakan format Indonesia (+62xxx)"
            )
        return v


class RequestOTPResponse(BaseModel):
    message: str = "Kode OTP telah dikirim ke nomor telepon Anda"
    phone_number: str
    expires_in_seconds: int = 300


class VerifyOTPRequest(BaseModel):
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=20,
        examples=["+6281234567890"],
    )
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        examples=["123456"],
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("0"):
            v = "+62" + v[1:]
        elif v.startswith("62"):
            v = "+" + v
        elif not v.startswith("+"):
            v = "+62" + v

        pattern = r"^\+62[0-9]{8,13}$"
        if not re.match(pattern, v):
            raise ValueError(
                "Nomor telepon tidak valid. Gunakan format Indonesia (+62xxx)"
            )
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    phone_number: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    language: str = "id"
    subscription_tier: str = "free"
    is_new_user: bool = False

    class Config:
        from_attributes = True


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class LogoutResponse(BaseModel):
    message: str = "Berhasil keluar"


TokenResponse.model_rebuild()
