import asyncio
from typing import Optional

import structlog
from celery import shared_task

from app.db.models import TranscriptionStatus
from app.db.session import AsyncSessionLocal
from app.services.story_service import StoryService
from app.services.transcription_service import TranscriptionService

logger = structlog.get_logger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def transcribe_story_task(self, story_id: str) -> dict:
    return run_async(_transcribe_story(self, story_id))


async def _transcribe_story(task, story_id: str) -> dict:
    logger.info("transcription_task_started", story_id=story_id)

    async with AsyncSessionLocal() as db:
        story_service = StoryService(db)

        try:
            story = await story_service.update_transcription_status(
                story_id=story_id,
                status=TranscriptionStatus.PROCESSING.value,
            )

            transcription_service = TranscriptionService()
            transcript = await transcription_service.transcribe_audio(
                audio_storage_key=story.audio_storage_key,
                language=story.language,
            )

            await story_service.update_transcription_status(
                story_id=story_id,
                status=TranscriptionStatus.COMPLETED.value,
                transcript=transcript,
            )

            logger.info(
                "transcription_task_completed",
                story_id=story_id,
                transcript_length=len(transcript),
            )

            return {
                "status": "success",
                "story_id": story_id,
                "transcript_length": len(transcript),
            }

        except Exception as e:
            error_message = str(e)
            logger.error(
                "transcription_task_failed",
                story_id=story_id,
                error=error_message,
                retry_count=task.request.retries,
            )

            if task.request.retries >= task.max_retries:
                await story_service.update_transcription_status(
                    story_id=story_id,
                    status=TranscriptionStatus.FAILED.value,
                    error=f"Gagal setelah {task.max_retries + 1} percobaan: {error_message}",
                )

                return {
                    "status": "failed",
                    "story_id": story_id,
                    "error": error_message,
                }

            raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def retry_failed_transcription_task(self, story_id: str) -> dict:
    return run_async(_retry_failed_transcription(self, story_id))


async def _retry_failed_transcription(task, story_id: str) -> dict:
    logger.info("retry_transcription_started", story_id=story_id)

    async with AsyncSessionLocal() as db:
        story_service = StoryService(db)

        from sqlalchemy import select
        from app.db.models import Story

        query = select(Story).where(Story.id == story_id)
        result = await db.execute(query)
        story = result.scalar_one_or_none()

        if not story:
            logger.error("story_not_found_for_retry", story_id=story_id)
            return {"status": "failed", "error": "Cerita tidak ditemukan"}

        if story.transcription_status != TranscriptionStatus.FAILED.value:
            logger.info(
                "story_not_in_failed_state",
                story_id=story_id,
                current_status=story.transcription_status,
            )
            return {
                "status": "skipped",
                "reason": "Cerita tidak dalam status gagal",
            }

        await story_service.update_transcription_status(
            story_id=story_id,
            status=TranscriptionStatus.PENDING.value,
            error=None,
        )

        transcribe_story_task.delay(story_id)

        return {"status": "queued", "story_id": story_id}
