from typing import AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import verify_access_token
from app.core.exceptions import UnauthorizedException, NotFoundException
from app.db.session import get_db
from app.db.models import User


async def get_current_user(
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException("Format token tidak valid")

    token = authorization.replace("Bearer ", "")
    user_id = verify_access_token(token)

    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundException("Pengguna tidak ditemukan")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.deleted_at is not None:
        raise UnauthorizedException("Akun telah dinonaktifkan")
    return current_user


async def get_optional_user(
    authorization: str = Header(None, description="Bearer token (optional)"),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not authorization:
        return None

    try:
        return await get_current_user(authorization, db)
    except (UnauthorizedException, NotFoundException):
        return None
