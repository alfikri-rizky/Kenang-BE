from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.v1.auth.schemas import (
    LogoutResponse,
    RefreshTokenRequest,
    RequestOTPRequest,
    RequestOTPResponse,
    TokenResponse,
    UserResponse,
    VerifyOTPRequest,
)
from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import verify_refresh_token
from app.services.auth_service import AuthService
from app.services.otp_service import OTPService

router = APIRouter()


@router.post(
    "/request-otp",
    response_model=RequestOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Kirim kode OTP ke nomor telepon",
    description="Mengirim kode OTP 6 digit ke nomor telepon untuk verifikasi. "
    "Rate limit: maksimal 5 permintaan per jam per nomor telepon.",
)
async def request_otp(
    request: RequestOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> RequestOTPResponse:
    otp_service = OTPService(db)
    await otp_service.create_and_send_otp(request.phone_number)

    return RequestOTPResponse(
        phone_number=request.phone_number,
        expires_in_seconds=settings.OTP_EXPIRY_MINUTES * 60,
    )


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Verifikasi kode OTP dan dapatkan token",
    description="Memverifikasi kode OTP dan mengembalikan access token serta refresh token. "
    "Jika pengguna baru, akun akan dibuat secara otomatis.",
)
async def verify_otp(
    request: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    otp_service = OTPService(db)
    await otp_service.verify_otp(request.phone_number, request.code)

    auth_service = AuthService(db)
    user, is_new_user = await auth_service.create_or_get_user(request.phone_number)

    access_token, refresh_token, expires_in = auth_service.generate_tokens(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserResponse(
            id=user.id,
            phone_number=user.phone_number,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            language=user.language,
            subscription_tier=user.subscription_tier,
            is_new_user=is_new_user,
        ),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Perbarui access token",
    description="Menggunakan refresh token untuk mendapatkan access token baru.",
)
async def refresh_token_endpoint(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user_id = verify_refresh_token(request.refresh_token)

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)

    if not user:
        raise UnauthorizedException("Pengguna tidak ditemukan")

    access_token, new_refresh_token, expires_in = auth_service.generate_tokens(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
        user=UserResponse(
            id=user.id,
            phone_number=user.phone_number,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            language=user.language,
            subscription_tier=user.subscription_tier,
            is_new_user=False,
        ),
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Keluar dari akun",
    description="Menginvalidasi sesi pengguna. "
    "Catatan: Pada implementasi stateless JWT, token tetap valid sampai expired.",
)
async def logout() -> LogoutResponse:
    return LogoutResponse()
