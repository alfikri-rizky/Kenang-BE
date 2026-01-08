from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CircleTypeEnum(str, Enum):
    KELUARGA = "keluarga"
    PASANGAN = "pasangan"
    SAHABAT = "sahabat"
    REKAN_KERJA = "rekan_kerja"
    KOMUNITAS = "komunitas"
    MENTOR = "mentor"
    PRIBADI = "pribadi"


class CirclePrivacyEnum(str, Enum):
    PRIVATE = "private"
    MEMBERS_ONLY = "members_only"
    LINK_ACCESS = "link_access"


class MemberRoleEnum(str, Enum):
    ADMIN = "admin"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class CreateCircleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: CircleTypeEnum
    description: Optional[str] = Field(None, max_length=500)
    cover_photo_url: Optional[str] = Field(None, max_length=500)
    privacy: CirclePrivacyEnum = CirclePrivacyEnum.MEMBERS_ONLY

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama lingkaran tidak boleh kosong")
        return v


class UpdateCircleRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    cover_photo_url: Optional[str] = Field(None, max_length=500)
    privacy: Optional[CirclePrivacyEnum] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Nama lingkaran tidak boleh kosong")
        return v


class CircleMemberResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    custom_label: Optional[str] = None
    joined_at: Optional[datetime] = None
    is_current_user: bool = False

    class Config:
        from_attributes = True


class CircleResponse(BaseModel):
    id: str
    name: str
    type: str
    description: Optional[str] = None
    cover_photo_url: Optional[str] = None
    privacy: str
    member_count: int = 0
    story_count: int = 0
    photo_count: int = 0
    current_user_role: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CircleDetailResponse(CircleResponse):
    members: List[CircleMemberResponse] = []
    invite_code: Optional[str] = None
    invite_code_expires_at: Optional[datetime] = None


class CircleListResponse(BaseModel):
    circles: List[CircleResponse]
    total: int


class AddMemberRequest(BaseModel):
    user_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: MemberRoleEnum = MemberRoleEnum.CONTRIBUTOR
    custom_label: Optional[str] = Field(None, max_length=50)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Nama tidak boleh kosong")
        return v


class UpdateMemberRequest(BaseModel):
    role: Optional[MemberRoleEnum] = None
    custom_label: Optional[str] = Field(None, max_length=50)


class MemberResponse(BaseModel):
    id: str
    circle_id: str
    user_id: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    custom_label: Optional[str] = None
    joined_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemberListResponse(BaseModel):
    members: List[MemberResponse]
    total: int


class CreateInviteRequest(BaseModel):
    role: MemberRoleEnum = MemberRoleEnum.CONTRIBUTOR
    custom_label: Optional[str] = Field(None, max_length=50)
    max_uses: int = Field(default=1, ge=1, le=100)


class InviteResponse(BaseModel):
    id: str
    circle_id: str
    invite_code: str
    invite_url: str
    assigned_role: str
    assigned_label: Optional[str] = None
    max_uses: int
    use_count: int
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JoinCircleRequest(BaseModel):
    invite_code: str = Field(..., min_length=6, max_length=20)


class JoinCircleResponse(BaseModel):
    message: str = "Berhasil bergabung ke lingkaran"
    circle: CircleResponse


class LeaveCircleResponse(BaseModel):
    message: str = "Berhasil keluar dari lingkaran"


class DeleteCircleResponse(BaseModel):
    message: str = "Lingkaran berhasil dihapus"
