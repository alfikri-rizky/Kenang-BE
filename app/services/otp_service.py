import random
import string
from datetime import datetime, timedelta
from typing import Optional

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessException, RateLimitException
from app.core.logging import mask_phone
from app.db.models import OTPCode

logger = structlog.get_logger(__name__)


class OTPService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_otp_code(self) -> str:
        return "".join(random.choices(string.digits, k=settings.OTP_LENGTH))

    async def _count_recent_attempts(self, phone_number: str) -> int:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        query = select(OTPCode).where(
            OTPCode.phone_number == phone_number,
            OTPCode.created_at >= one_hour_ago,
        )
        result = await self.db.execute(query)
        return len(result.scalars().all())

    async def _get_active_otp(self, phone_number: str) -> Optional[OTPCode]:
        now = datetime.utcnow()
        query = (
            select(OTPCode)
            .where(
                OTPCode.phone_number == phone_number,
                OTPCode.expires_at > now,
                OTPCode.verified_at.is_(None),
            )
            .order_by(OTPCode.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_and_send_otp(self, phone_number: str) -> OTPCode:
        recent_attempts = await self._count_recent_attempts(phone_number)
        if recent_attempts >= settings.OTP_MAX_ATTEMPTS_PER_HOUR:
            logger.warning(
                "otp_rate_limit_exceeded",
                phone=mask_phone(phone_number),
                attempts=recent_attempts,
            )
            raise RateLimitException("Terlalu banyak percobaan. Coba lagi dalam 1 jam.")

        existing_otp = await self._get_active_otp(phone_number)
        if existing_otp:
            time_since_created = datetime.utcnow() - existing_otp.created_at
            if time_since_created < timedelta(seconds=60):
                raise BusinessException(
                    code="OTP_COOLDOWN",
                    message="Tunggu 60 detik sebelum meminta kode OTP baru",
                )

        code = self._generate_otp_code()
        expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        otp = OTPCode(
            phone_number=phone_number,
            code=code,
            expires_at=expires_at,
            attempts="0",
        )
        self.db.add(otp)
        await self.db.commit()
        await self.db.refresh(otp)

        await self._send_otp_sms(phone_number, code)

        logger.info(
            "otp_created",
            phone=mask_phone(phone_number),
            otp_id=otp.id,
        )

        return otp

    async def _send_otp_sms(self, phone_number: str, code: str) -> bool:
        if settings.APP_ENV == "development":
            logger.info(
                "otp_sms_skipped_dev_mode",
                phone=mask_phone(phone_number),
                code=code,
            )
            return True

        if settings.SMS_PROVIDER == "fazpass":
            return await self._send_via_fazpass(phone_number, code)
        else:
            logger.warning("unknown_sms_provider", provider=settings.SMS_PROVIDER)
            return False

    async def _send_via_fazpass(self, phone_number: str, code: str) -> bool:
        if not settings.FAZPASS_API_KEY or not settings.FAZPASS_GATEWAY_KEY:
            logger.error("fazpass_credentials_missing")
            return False

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.fazpass.com/v1/otp/request",
                    headers={
                        "Authorization": f"Bearer {settings.FAZPASS_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "gateway_key": settings.FAZPASS_GATEWAY_KEY,
                        "phone": phone_number,
                        "otp": code,
                        "message": f"Kode OTP Kenang Anda adalah: {code}. Berlaku 5 menit. Jangan bagikan ke siapapun.",
                    },
                )

                if response.status_code == 200:
                    logger.info(
                        "otp_sms_sent",
                        phone=mask_phone(phone_number),
                        provider="fazpass",
                    )
                    return True
                else:
                    logger.error(
                        "fazpass_send_failed",
                        status_code=response.status_code,
                        response=response.text,
                    )
                    return False

        except httpx.RequestError as e:
            logger.error("fazpass_request_error", error=str(e))
            return False

    async def verify_otp(self, phone_number: str, code: str) -> OTPCode:
        otp = await self._get_active_otp(phone_number)

        if not otp:
            logger.warning(
                "otp_not_found",
                phone=mask_phone(phone_number),
            )
            raise BusinessException(
                code="OTP_NOT_FOUND",
                message="Kode OTP tidak ditemukan atau sudah kadaluarsa. Kirim ulang kode.",
            )

        current_attempts = int(otp.attempts)
        if current_attempts >= 3:
            raise BusinessException(
                code="OTP_MAX_ATTEMPTS",
                message="Terlalu banyak percobaan salah. Minta kode OTP baru.",
            )

        if otp.code != code:
            otp.attempts = str(current_attempts + 1)
            await self.db.commit()

            logger.warning(
                "otp_invalid_code",
                phone=mask_phone(phone_number),
                attempts=current_attempts + 1,
            )
            raise BusinessException(
                code="OTP_INVALID",
                message="Kode OTP salah. Coba lagi.",
            )

        otp.verified_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(otp)

        logger.info(
            "otp_verified",
            phone=mask_phone(phone_number),
            otp_id=otp.id,
        )

        return otp
