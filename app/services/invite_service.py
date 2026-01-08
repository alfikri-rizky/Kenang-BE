import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessException, NotFoundException
from app.db.models import Circle, CircleMembership, Invite, MemberRole

logger = structlog.get_logger(__name__)


class InviteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_invite_code(self, length: int = 12) -> str:
        chars = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(chars) for _ in range(length))

    async def create_invite(
        self,
        circle_id: str,
        invited_by: str,
        role: str = MemberRole.CONTRIBUTOR.value,
        custom_label: Optional[str] = None,
        max_uses: int = 1,
        expires_in_days: int = 7,
    ) -> Invite:
        query = select(Circle).where(
            Circle.id == circle_id,
            Circle.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        circle = result.scalar_one_or_none()

        if not circle:
            raise NotFoundException("Lingkaran tidak ditemukan")

        invite_code = self._generate_invite_code()

        while await self._code_exists(invite_code):
            invite_code = self._generate_invite_code()

        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        invite = Invite(
            circle_id=circle_id,
            invite_code=invite_code,
            invited_by=invited_by,
            assigned_role=role,
            assigned_label=custom_label,
            max_uses=max_uses,
            use_count=0,
            expires_at=expires_at,
        )
        self.db.add(invite)
        await self.db.commit()
        await self.db.refresh(invite)

        logger.info(
            "invite_created",
            circle_id=circle_id,
            invite_code=invite_code,
            invited_by=invited_by,
        )

        return invite

    async def _code_exists(self, code: str) -> bool:
        query = select(Invite).where(Invite.invite_code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_invite_by_code(self, invite_code: str) -> Invite:
        query = select(Invite).where(Invite.invite_code == invite_code)
        result = await self.db.execute(query)
        invite = result.scalar_one_or_none()

        if not invite:
            raise NotFoundException("Kode undangan tidak ditemukan")

        return invite

    async def validate_invite(self, invite_code: str) -> Invite:
        invite = await self.get_invite_by_code(invite_code)

        if invite.expires_at and invite.expires_at < datetime.utcnow():
            raise BusinessException(
                code="INVITE_EXPIRED",
                message="Kode undangan sudah kadaluarsa",
            )

        if invite.use_count >= invite.max_uses:
            raise BusinessException(
                code="INVITE_MAX_USES_REACHED",
                message="Kode undangan sudah mencapai batas penggunaan maksimal",
            )

        query = select(Circle).where(
            Circle.id == invite.circle_id,
            Circle.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        circle = result.scalar_one_or_none()

        if not circle:
            raise BusinessException(
                code="CIRCLE_DELETED",
                message="Lingkaran sudah tidak ada",
            )

        return invite

    async def join_circle_via_invite(self, invite_code: str, user_id: str) -> Circle:
        invite = await self.validate_invite(invite_code)

        existing_query = select(CircleMembership).where(
            CircleMembership.circle_id == invite.circle_id,
            CircleMembership.user_id == user_id,
        )
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise BusinessException(
                code="ALREADY_MEMBER",
                message="Kamu sudah menjadi anggota lingkaran ini",
            )

        membership = CircleMembership(
            circle_id=invite.circle_id,
            user_id=user_id,
            role=invite.assigned_role,
            custom_label=invite.assigned_label,
            invited_by=invite.invited_by,
            joined_at=datetime.utcnow(),
        )
        self.db.add(membership)

        invite.use_count += 1
        await self.db.commit()

        circle_query = select(Circle).where(Circle.id == invite.circle_id)
        circle_result = await self.db.execute(circle_query)
        circle = circle_result.scalar_one()

        logger.info(
            "user_joined_via_invite",
            circle_id=invite.circle_id,
            user_id=user_id,
            invite_code=invite_code,
        )

        return circle

    async def get_circle_invites(self, circle_id: str) -> list[Invite]:
        query = (
            select(Invite)
            .where(Invite.circle_id == circle_id)
            .order_by(Invite.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def revoke_invite(self, invite_id: str, user_id: str) -> None:
        query = select(Invite).where(Invite.id == invite_id)
        result = await self.db.execute(query)
        invite = result.scalar_one_or_none()

        if not invite:
            raise NotFoundException("Undangan tidak ditemukan")

        await self.db.delete(invite)
        await self.db.commit()

        logger.info(
            "invite_revoked",
            invite_id=invite_id,
            circle_id=invite.circle_id,
            user_id=user_id,
        )
