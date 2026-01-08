from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.users.schemas import (
    DeleteAccountRequest,
    DeleteAccountResponse,
    UpdateProfileRequest,
    UpdateProfileResponse,
    UserProfileResponse,
    UserStatsResponse,
)
from app.db.models import User
from app.services.user_service import UserService

router = APIRouter()


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Dapatkan profil pengguna saat ini",
    description="Mengembalikan informasi profil lengkap pengguna yang sedang login.",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    return UserProfileResponse.from_orm(current_user)


@router.patch(
    "/me",
    response_model=UpdateProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Perbarui profil pengguna",
    description="Memperbarui informasi profil pengguna. Semua field bersifat opsional.",
)
async def update_my_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UpdateProfileResponse:
    user_service = UserService(db)

    updated_user = await user_service.update_profile(
        user_id=current_user.id,
        display_name=request.display_name,
        avatar_url=request.avatar_url,
        language=request.language,
        timezone=request.timezone,
    )

    return UpdateProfileResponse(
        user=UserProfileResponse.from_orm(updated_user),
    )


@router.delete(
    "/me",
    response_model=DeleteAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Hapus akun pengguna",
    description="Soft delete akun pengguna. Data tidak dihapus permanen tetapi tidak dapat diakses lagi.",
)
async def delete_my_account(
    request: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeleteAccountResponse:
    user_service = UserService(db)
    await user_service.delete_account(current_user.id)

    return DeleteAccountResponse()


@router.get(
    "/me/stats",
    response_model=UserStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Dapatkan statistik pengguna",
    description="Mengembalikan statistik penggunaan: jumlah lingkaran, foto, cerita, dan sisa kuota.",
)
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserStatsResponse:
    user_service = UserService(db)
    stats = await user_service.get_user_stats(current_user.id)

    return UserStatsResponse(**stats)
