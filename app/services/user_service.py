from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.logging import mask_phone
from app.db.models import (
    Circle,
    CircleMembership,
    Photo,
    Story,
    SubscriptionTier,
    User,
)

logger = structlog.get_logger(__name__)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: str) -> User:
        query = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException("Pengguna tidak ditemukan")

        return user

    async def update_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        language: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> User:
        user = await self.get_user_by_id(user_id)

        if display_name is not None:
            user.display_name = display_name
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if language is not None:
            user.language = language
        if timezone is not None:
            user.timezone = timezone

        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(
            "user_profile_updated",
            user_id=user_id,
            phone=mask_phone(user.phone_number),
        )

        return user

    async def delete_account(self, user_id: str) -> None:
        user = await self.get_user_by_id(user_id)

        user.deleted_at = datetime.utcnow()
        await self.db.commit()

        logger.info(
            "user_account_deleted",
            user_id=user_id,
            phone=mask_phone(user.phone_number),
        )

    async def get_user_stats(self, user_id: str) -> dict:
        circles_query = (
            select(func.count(CircleMembership.id))
            .where(CircleMembership.user_id == user_id)
            .join(Circle, Circle.id == CircleMembership.circle_id)
            .where(Circle.deleted_at.is_(None))
        )
        circles_result = await self.db.execute(circles_query)
        total_circles = circles_result.scalar() or 0

        user_circle_ids_subquery = (
            select(CircleMembership.circle_id)
            .where(CircleMembership.user_id == user_id)
            .subquery()
        )

        photos_query = select(func.count(Photo.id)).where(
            Photo.circle_id.in_(select(user_circle_ids_subquery)),
            Photo.deleted_at.is_(None),
        )
        photos_result = await self.db.execute(photos_query)
        total_photos = photos_result.scalar() or 0

        stories_query = select(func.count(Story.id)).where(
            Story.circle_id.in_(select(user_circle_ids_subquery)),
            Story.deleted_at.is_(None),
        )
        stories_result = await self.db.execute(stories_query)
        total_stories = stories_result.scalar() or 0

        user = await self.get_user_by_id(user_id)
        tier = user.subscription_tier

        if tier == SubscriptionTier.FREE.value:
            max_circles = settings.FREE_TIER_MAX_CIRCLES
            max_photos = settings.FREE_TIER_MAX_PHOTOS
            max_stories = settings.FREE_TIER_MAX_STORIES
        elif tier == SubscriptionTier.PERSONAL.value:
            max_circles = settings.PERSONAL_TIER_MAX_CIRCLES
            max_photos = settings.PERSONAL_TIER_MAX_PHOTOS
            max_stories = -1
        elif tier == SubscriptionTier.PLUS.value:
            max_circles = settings.PLUS_TIER_MAX_CIRCLES
            max_photos = settings.PLUS_TIER_MAX_PHOTOS
            max_stories = -1
        else:
            max_circles = -1
            max_photos = -1
            max_stories = -1

        return {
            "total_circles": total_circles,
            "total_photos": total_photos,
            "total_stories": total_stories,
            "circles_remaining": max_circles - total_circles if max_circles > 0 else -1,
            "photos_remaining": max_photos - total_photos if max_photos > 0 else -1,
            "stories_remaining": max_stories - total_stories if max_stories > 0 else -1,
        }
