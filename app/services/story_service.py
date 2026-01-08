from datetime import datetime
from typing import List, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import BusinessException, ForbiddenException, NotFoundException
from app.db.models import MemberRole, Photo, Story, SubscriptionTier, TranscriptionStatus, User
from app.services.circle_service import CircleService
from app.services.storage_service import StorageService

logger = structlog.get_logger(__name__)


class StoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.circle_service = CircleService(db)
        self.storage_service = StorageService()

    async def _check_story_limit(self, user_id: str) -> None:
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException("Pengguna tidak ditemukan")

        count_query = (
            select(func.count(Story.id))
            .where(Story.recorded_by == user_id, Story.deleted_at.is_(None))
        )
        count_result = await self.db.execute(count_query)
        current_stories = count_result.scalar() or 0

        tier = user.subscription_tier
        if tier == SubscriptionTier.FREE.value:
            max_stories = settings.FREE_TIER_MAX_STORIES
        elif tier == SubscriptionTier.PERSONAL.value:
            max_stories = 100
        elif tier == SubscriptionTier.PLUS.value:
            max_stories = 500
        else:
            return

        if current_stories >= max_stories:
            raise BusinessException(
                code="STORY_LIMIT_REACHED",
                message=f"Batas cerita tercapai ({max_stories}). Upgrade untuk membuat lebih banyak.",
            )

    async def create_story(
        self,
        user_id: str,
        circle_id: str,
        audio_storage_key: str,
        photo_id: Optional[str] = None,
        prompt_used: Optional[str] = None,
        audio_duration_seconds: Optional[int] = None,
        language: str = "id",
    ) -> Story:
        await self.circle_service._check_access(
            circle_id, user_id, required_role=MemberRole.CONTRIBUTOR.value
        )

        await self._check_story_limit(user_id)

        file_exists = await self.storage_service.verify_file_exists(audio_storage_key)
        if not file_exists:
            raise NotFoundException("Audio tidak ditemukan di storage. Upload mungkin gagal.")

        if photo_id:
            photo_query = select(Photo).where(
                Photo.id == photo_id,
                Photo.circle_id == circle_id,
                Photo.deleted_at.is_(None),
            )
            photo_result = await self.db.execute(photo_query)
            photo = photo_result.scalar_one_or_none()
            if not photo:
                raise NotFoundException("Foto tidak ditemukan dalam lingkaran ini")

        audio_url = await self.storage_service.generate_download_url(audio_storage_key)

        story = Story(
            circle_id=circle_id,
            photo_id=photo_id,
            recorded_by=user_id,
            audio_url=audio_url,
            audio_storage_key=audio_storage_key,
            audio_duration_seconds=audio_duration_seconds,
            prompt_used=prompt_used,
            language=language,
            transcription_status=TranscriptionStatus.PENDING.value,
        )

        self.db.add(story)
        await self.db.commit()
        await self.db.refresh(story)

        logger.info(
            "story_created",
            story_id=story.id,
            circle_id=circle_id,
            user_id=user_id,
        )

        return story

    async def get_story_by_id(self, story_id: str, user_id: str) -> Story:
        query = (
            select(Story)
            .where(Story.id == story_id, Story.deleted_at.is_(None))
            .options(selectinload(Story.photo), selectinload(Story.recorder))
        )
        result = await self.db.execute(query)
        story = result.scalar_one_or_none()

        if not story:
            raise NotFoundException("Cerita tidak ditemukan")

        await self.circle_service._check_access(story.circle_id, user_id)

        return story

    async def list_stories(
        self,
        circle_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        photo_id: Optional[str] = None,
    ) -> tuple[List[Story], int]:
        await self.circle_service._check_access(circle_id, user_id)

        base_query = select(Story).where(
            Story.circle_id == circle_id,
            Story.deleted_at.is_(None),
        )

        if photo_id:
            base_query = base_query.where(Story.photo_id == photo_id)

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        stories_query = (
            base_query
            .options(selectinload(Story.photo), selectinload(Story.recorder))
            .order_by(Story.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        stories_result = await self.db.execute(stories_query)
        stories = list(stories_result.scalars().all())

        return stories, total

    async def update_transcript(
        self,
        story_id: str,
        user_id: str,
        transcript_edited: str,
    ) -> Story:
        story = await self.get_story_by_id(story_id, user_id)

        await self.circle_service._check_access(
            story.circle_id, user_id, required_role=MemberRole.CONTRIBUTOR.value
        )

        story.transcript_edited = transcript_edited
        story.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(story)

        logger.info(
            "story_transcript_updated",
            story_id=story_id,
            user_id=user_id,
        )

        return story

    async def delete_story(self, story_id: str, user_id: str) -> None:
        story = await self.get_story_by_id(story_id, user_id)

        await self.circle_service._check_access(
            story.circle_id, user_id, required_role=MemberRole.CONTRIBUTOR.value
        )

        story.deleted_at = datetime.utcnow()
        await self.db.commit()

        logger.info(
            "story_deleted",
            story_id=story_id,
            user_id=user_id,
        )

    async def get_transcription_status(self, story_id: str, user_id: str) -> dict:
        story = await self.get_story_by_id(story_id, user_id)

        return {
            "status": story.transcription_status,
            "error": story.transcription_error,
            "has_transcript": story.transcript_original is not None,
        }

    async def update_transcription_status(
        self,
        story_id: str,
        status: str,
        transcript: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Story:
        query = select(Story).where(Story.id == story_id)
        result = await self.db.execute(query)
        story = result.scalar_one_or_none()

        if not story:
            raise NotFoundException("Cerita tidak ditemukan")

        story.transcription_status = status
        story.updated_at = datetime.utcnow()

        if transcript:
            story.transcript_original = transcript
        if error:
            story.transcription_error = error

        await self.db.commit()
        await self.db.refresh(story)

        logger.info(
            "story_transcription_status_updated",
            story_id=story_id,
            status=status,
        )

        return story

    async def get_audio_download_url(self, story: Story) -> str:
        return await self.storage_service.generate_download_url(story.audio_storage_key)
