from datetime import datetime
from typing import Optional, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.logging import mask_phone
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.db.models import User

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        query = select(User).where(
            User.phone_number == phone_number,
            User.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        query = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_or_get_user(self, phone_number: str) -> Tuple[User, bool]:
        existing_user = await self.get_user_by_phone(phone_number)

        if existing_user:
            existing_user.phone_verified = True
            existing_user.last_active_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing_user)

            logger.info(
                "user_logged_in",
                user_id=existing_user.id,
                phone=mask_phone(phone_number),
            )
            return existing_user, False

        new_user = User(
            phone_number=phone_number,
            phone_verified=True,
            last_active_at=datetime.utcnow(),
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        logger.info(
            "user_registered",
            user_id=new_user.id,
            phone=mask_phone(phone_number),
        )
        return new_user, True

    def generate_tokens(self, user_id: str) -> Tuple[str, str, int]:
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return access_token, refresh_token, expires_in

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str, int]:
        user_id = verify_refresh_token(refresh_token)

        user = await self.get_user_by_id(user_id)
        if not user:
            raise UnauthorizedException("Pengguna tidak ditemukan")

        user.last_active_at = datetime.utcnow()
        await self.db.commit()

        return self.generate_tokens(user_id)

    async def update_last_active(self, user_id: str) -> None:
        user = await self.get_user_by_id(user_id)
        if user:
            user.last_active_at = datetime.utcnow()
            await self.db.commit()
