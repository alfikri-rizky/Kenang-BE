from datetime import datetime
from typing import List, Optional, Tuple

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import BusinessException, ForbiddenException, NotFoundException
from app.db.models import (
    Circle,
    CircleMember,
    CircleMembership,
    MemberRole,
    Photo,
    Story,
    SubscriptionTier,
    User,
)

logger = structlog.get_logger(__name__)


class CircleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _check_circle_limit(self, user_id: str) -> None:
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException("Pengguna tidak ditemukan")

        count_query = (
            select(func.count(CircleMembership.id))
            .where(CircleMembership.user_id == user_id)
            .join(Circle, Circle.id == CircleMembership.circle_id)
            .where(Circle.deleted_at.is_(None))
        )
        count_result = await self.db.execute(count_query)
        current_circles = count_result.scalar() or 0

        tier = user.subscription_tier
        if tier == SubscriptionTier.FREE.value:
            max_circles = settings.FREE_TIER_MAX_CIRCLES
        elif tier == SubscriptionTier.PERSONAL.value:
            max_circles = settings.PERSONAL_TIER_MAX_CIRCLES
        elif tier == SubscriptionTier.PLUS.value:
            max_circles = settings.PLUS_TIER_MAX_CIRCLES
        else:
            return

        if current_circles >= max_circles:
            raise BusinessException(
                code="CIRCLE_LIMIT_REACHED",
                message=f"Batas lingkaran tercapai ({max_circles}). Upgrade untuk membuat lebih banyak.",
            )

    async def create_circle(
        self,
        user_id: str,
        name: str,
        circle_type: str,
        description: Optional[str] = None,
        cover_photo_url: Optional[str] = None,
        privacy: str = "members_only",
    ) -> Circle:
        await self._check_circle_limit(user_id)

        circle = Circle(
            name=name,
            type=circle_type,
            description=description,
            cover_photo_url=cover_photo_url,
            privacy=privacy,
            created_by=user_id,
        )
        self.db.add(circle)
        await self.db.flush()

        membership = CircleMembership(
            circle_id=circle.id,
            user_id=user_id,
            role=MemberRole.ADMIN.value,
            joined_at=datetime.utcnow(),
        )
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(circle)

        logger.info(
            "circle_created",
            circle_id=circle.id,
            user_id=user_id,
            circle_type=circle_type,
        )

        return circle

    async def get_circle_by_id(
        self, circle_id: str, user_id: Optional[str] = None
    ) -> Circle:
        query = (
            select(Circle)
            .where(Circle.id == circle_id, Circle.deleted_at.is_(None))
            .options(selectinload(Circle.memberships))
        )
        result = await self.db.execute(query)
        circle = result.scalar_one_or_none()

        if not circle:
            raise NotFoundException("Lingkaran tidak ditemukan")

        if user_id:
            await self._check_access(circle_id, user_id)

        return circle

    async def _check_access(
        self, circle_id: str, user_id: str, required_role: Optional[str] = None
    ) -> CircleMembership:
        query = select(CircleMembership).where(
            CircleMembership.circle_id == circle_id,
            CircleMembership.user_id == user_id,
        )
        result = await self.db.execute(query)
        membership = result.scalar_one_or_none()

        if not membership:
            raise ForbiddenException("Kamu bukan anggota lingkaran ini")

        if required_role:
            if required_role == MemberRole.ADMIN.value:
                if membership.role != MemberRole.ADMIN.value:
                    raise ForbiddenException("Hanya admin yang bisa melakukan aksi ini")
            elif required_role == MemberRole.CONTRIBUTOR.value:
                if membership.role not in [
                    MemberRole.ADMIN.value,
                    MemberRole.CONTRIBUTOR.value,
                ]:
                    raise ForbiddenException(
                        "Kamu tidak punya izin untuk melakukan aksi ini"
                    )

        return membership

    async def get_user_circles(self, user_id: str) -> List[Circle]:
        query = (
            select(Circle)
            .join(CircleMembership, CircleMembership.circle_id == Circle.id)
            .where(
                CircleMembership.user_id == user_id,
                Circle.deleted_at.is_(None),
            )
            .order_by(Circle.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_circle(
        self,
        circle_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        cover_photo_url: Optional[str] = None,
        privacy: Optional[str] = None,
    ) -> Circle:
        await self._check_access(circle_id, user_id, required_role=MemberRole.ADMIN.value)

        circle = await self.get_circle_by_id(circle_id)

        if name is not None:
            circle.name = name
        if description is not None:
            circle.description = description
        if cover_photo_url is not None:
            circle.cover_photo_url = cover_photo_url
        if privacy is not None:
            circle.privacy = privacy

        circle.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(circle)

        logger.info("circle_updated", circle_id=circle_id, user_id=user_id)

        return circle

    async def delete_circle(self, circle_id: str, user_id: str) -> None:
        await self._check_access(circle_id, user_id, required_role=MemberRole.ADMIN.value)

        circle = await self.get_circle_by_id(circle_id)
        circle.deleted_at = datetime.utcnow()
        await self.db.commit()

        logger.info("circle_deleted", circle_id=circle_id, user_id=user_id)

    async def add_member(
        self,
        circle_id: str,
        admin_user_id: str,
        user_id: Optional[str] = None,
        name: Optional[str] = None,
        role: str = MemberRole.CONTRIBUTOR.value,
        custom_label: Optional[str] = None,
    ) -> Tuple[Optional[CircleMembership], Optional[CircleMember]]:
        await self._check_access(circle_id, admin_user_id, required_role=MemberRole.ADMIN.value)

        if user_id:
            existing_query = select(CircleMembership).where(
                CircleMembership.circle_id == circle_id,
                CircleMembership.user_id == user_id,
            )
            existing_result = await self.db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                raise BusinessException(
                    code="MEMBER_ALREADY_EXISTS",
                    message="Pengguna sudah menjadi anggota lingkaran ini",
                )

            membership = CircleMembership(
                circle_id=circle_id,
                user_id=user_id,
                role=role,
                custom_label=custom_label,
                invited_by=admin_user_id,
                joined_at=datetime.utcnow(),
            )
            self.db.add(membership)
            await self.db.commit()
            await self.db.refresh(membership)

            logger.info(
                "member_added",
                circle_id=circle_id,
                user_id=user_id,
                role=role,
            )

            return membership, None

        else:
            circle_member = CircleMember(
                circle_id=circle_id,
                name=name,
                custom_label=custom_label,
                created_by=admin_user_id,
            )
            self.db.add(circle_member)
            await self.db.commit()
            await self.db.refresh(circle_member)

            logger.info(
                "non_registered_member_added",
                circle_id=circle_id,
                name=name,
            )

            return None, circle_member

    async def get_circle_members(
        self, circle_id: str, user_id: str
    ) -> Tuple[List[CircleMembership], List[CircleMember]]:
        await self._check_access(circle_id, user_id)

        memberships_query = (
            select(CircleMembership)
            .where(CircleMembership.circle_id == circle_id)
            .options(selectinload(CircleMembership.user))
        )
        memberships_result = await self.db.execute(memberships_query)
        memberships = list(memberships_result.scalars().all())

        circle_members_query = select(CircleMember).where(
            CircleMember.circle_id == circle_id
        )
        circle_members_result = await self.db.execute(circle_members_query)
        circle_members = list(circle_members_result.scalars().all())

        return memberships, circle_members

    async def update_member_role(
        self,
        circle_id: str,
        membership_id: str,
        admin_user_id: str,
        role: Optional[str] = None,
        custom_label: Optional[str] = None,
    ) -> CircleMembership:
        await self._check_access(circle_id, admin_user_id, required_role=MemberRole.ADMIN.value)

        query = select(CircleMembership).where(CircleMembership.id == membership_id)
        result = await self.db.execute(query)
        membership = result.scalar_one_or_none()

        if not membership or membership.circle_id != circle_id:
            raise NotFoundException("Anggota tidak ditemukan")

        if role is not None:
            membership.role = role
        if custom_label is not None:
            membership.custom_label = custom_label

        await self.db.commit()
        await self.db.refresh(membership)

        logger.info(
            "member_role_updated",
            circle_id=circle_id,
            membership_id=membership_id,
            new_role=role,
        )

        return membership

    async def remove_member(
        self, circle_id: str, membership_id: str, admin_user_id: str
    ) -> None:
        await self._check_access(circle_id, admin_user_id, required_role=MemberRole.ADMIN.value)

        query = select(CircleMembership).where(CircleMembership.id == membership_id)
        result = await self.db.execute(query)
        membership = result.scalar_one_or_none()

        if not membership or membership.circle_id != circle_id:
            raise NotFoundException("Anggota tidak ditemukan")

        if membership.role == MemberRole.ADMIN.value:
            admin_count_query = select(func.count(CircleMembership.id)).where(
                CircleMembership.circle_id == circle_id,
                CircleMembership.role == MemberRole.ADMIN.value,
            )
            admin_count_result = await self.db.execute(admin_count_query)
            admin_count = admin_count_result.scalar() or 0

            if admin_count <= 1:
                raise BusinessException(
                    code="LAST_ADMIN",
                    message="Tidak bisa menghapus admin terakhir. Transfer admin ke anggota lain terlebih dahulu.",
                )

        await self.db.delete(membership)
        await self.db.commit()

        logger.info(
            "member_removed",
            circle_id=circle_id,
            membership_id=membership_id,
        )

    async def leave_circle(self, circle_id: str, user_id: str) -> None:
        membership = await self._check_access(circle_id, user_id)

        if membership.role == MemberRole.ADMIN.value:
            admin_count_query = select(func.count(CircleMembership.id)).where(
                CircleMembership.circle_id == circle_id,
                CircleMembership.role == MemberRole.ADMIN.value,
            )
            admin_count_result = await self.db.execute(admin_count_query)
            admin_count = admin_count_result.scalar() or 0

            if admin_count <= 1:
                raise BusinessException(
                    code="LAST_ADMIN",
                    message="Kamu adalah admin terakhir. Transfer admin ke anggota lain sebelum keluar.",
                )

        await self.db.delete(membership)
        await self.db.commit()

        logger.info("user_left_circle", circle_id=circle_id, user_id=user_id)

    async def get_circle_stats(self, circle_id: str) -> dict:
        member_count_query = select(func.count(CircleMembership.id)).where(
            CircleMembership.circle_id == circle_id
        )
        member_count_result = await self.db.execute(member_count_query)
        member_count = member_count_result.scalar() or 0

        photo_count_query = select(func.count(Photo.id)).where(
            Photo.circle_id == circle_id,
            Photo.deleted_at.is_(None),
        )
        photo_count_result = await self.db.execute(photo_count_query)
        photo_count = photo_count_result.scalar() or 0

        story_count_query = select(func.count(Story.id)).where(
            Story.circle_id == circle_id,
            Story.deleted_at.is_(None),
        )
        story_count_result = await self.db.execute(story_count_query)
        story_count = story_count_result.scalar() or 0

        return {
            "member_count": member_count,
            "photo_count": photo_count,
            "story_count": story_count,
        }
