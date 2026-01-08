from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.stories.schemas import (
    CreateStoryRequest,
    PhotoInfo,
    RecorderInfo,
    StoryListResponse,
    StoryResponse,
    TranscriptionStatusResponse,
    UpdateTranscriptRequest,
)
from app.db.models import User
from app.services.storage_service import StorageService
from app.services.story_service import StoryService
from app.tasks.transcription import transcribe_story_task

router = APIRouter()


def _build_story_response(story, audio_url: str) -> StoryResponse:
    recorder_info = None
    if story.recorder:
        recorder_info = RecorderInfo(
            id=story.recorder.id,
            name=story.recorder.name,
            avatar_url=story.recorder.avatar_url,
        )

    photo_info = None
    if story.photo:
        photo_info = PhotoInfo(
            id=story.photo.id,
            storage_key=story.photo.storage_key,
            thumbnail_key=story.photo.thumbnail_key,
            caption=story.photo.caption,
        )

    return StoryResponse(
        id=story.id,
        circle_id=story.circle_id,
        photo_id=story.photo_id,
        recorded_by=story.recorded_by,
        audio_url=audio_url,
        audio_storage_key=story.audio_storage_key,
        audio_duration_seconds=story.audio_duration_seconds,
        transcript_original=story.transcript_original,
        transcript_edited=story.transcript_edited,
        transcription_status=story.transcription_status,
        transcription_error=story.transcription_error,
        prompt_used=story.prompt_used,
        language=story.language,
        is_published=story.is_published,
        created_at=story.created_at,
        updated_at=story.updated_at,
        recorder=recorder_info,
        photo=photo_info,
    )


@router.post(
    "/stories",
    response_model=StoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat cerita baru",
    description="Membuat cerita baru dengan audio yang sudah diupload dan memulai proses transkripsi.",
)
async def create_story(
    request: CreateStoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoryResponse:
    story_service = StoryService(db)

    story = await story_service.create_story(
        user_id=current_user.id,
        circle_id=request.circle_id,
        audio_storage_key=request.audio_storage_key,
        photo_id=request.photo_id,
        prompt_used=request.prompt_used,
        audio_duration_seconds=request.audio_duration_seconds,
        language=request.language,
    )

    transcribe_story_task.delay(story.id)

    audio_url = await story_service.get_audio_download_url(story)

    return _build_story_response(story, audio_url)


@router.get(
    "/stories",
    response_model=StoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Daftar cerita dalam lingkaran",
    description="Mengambil daftar cerita dalam lingkaran dengan pagination.",
)
async def list_stories(
    circle_id: str = Query(..., description="ID lingkaran"),
    photo_id: Optional[str] = Query(None, description="Filter berdasarkan foto"),
    skip: int = Query(0, ge=0, description="Jumlah data yang dilewati"),
    limit: int = Query(50, ge=1, le=100, description="Jumlah data maksimal"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoryListResponse:
    story_service = StoryService(db)
    storage_service = StorageService()

    stories, total = await story_service.list_stories(
        circle_id=circle_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        photo_id=photo_id,
    )

    story_responses = []
    for story in stories:
        audio_url = await storage_service.generate_download_url(story.audio_storage_key)
        story_responses.append(_build_story_response(story, audio_url))

    return StoryListResponse(
        stories=story_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/stories/{story_id}",
    response_model=StoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Detail cerita",
    description="Mengambil detail cerita berdasarkan ID.",
)
async def get_story(
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoryResponse:
    story_service = StoryService(db)

    story = await story_service.get_story_by_id(story_id, current_user.id)
    audio_url = await story_service.get_audio_download_url(story)

    return _build_story_response(story, audio_url)


@router.get(
    "/stories/{story_id}/status",
    response_model=TranscriptionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Status transkripsi",
    description="Mengecek status proses transkripsi cerita.",
)
async def get_transcription_status(
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TranscriptionStatusResponse:
    story_service = StoryService(db)

    status_info = await story_service.get_transcription_status(
        story_id, current_user.id
    )

    return TranscriptionStatusResponse(
        status=status_info["status"],
        error=status_info["error"],
        has_transcript=status_info["has_transcript"],
    )


@router.patch(
    "/stories/{story_id}",
    response_model=StoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update transkrip cerita",
    description="Memperbarui transkrip cerita yang sudah diedit.",
)
async def update_story_transcript(
    story_id: str,
    request: UpdateTranscriptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoryResponse:
    story_service = StoryService(db)

    story = await story_service.update_transcript(
        story_id=story_id,
        user_id=current_user.id,
        transcript_edited=request.transcript_edited,
    )

    audio_url = await story_service.get_audio_download_url(story)

    return _build_story_response(story, audio_url)


@router.delete(
    "/stories/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus cerita",
    description="Menghapus cerita (soft delete).",
)
async def delete_story(
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    story_service = StoryService(db)
    await story_service.delete_story(story_id, current_user.id)


@router.post(
    "/stories/{story_id}/retry",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Ulangi transkripsi",
    description="Mengulangi proses transkripsi untuk cerita yang gagal.",
)
async def retry_transcription(
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    story_service = StoryService(db)

    status_info = await story_service.get_transcription_status(
        story_id, current_user.id
    )

    if status_info["status"] != "failed":
        return {
            "success": False,
            "message": "Hanya cerita dengan status gagal yang bisa diulangi transkripsinya.",
        }

    from app.db.models import TranscriptionStatus

    await story_service.update_transcription_status(
        story_id=story_id,
        status=TranscriptionStatus.PENDING.value,
        error=None,
    )

    transcribe_story_task.delay(story_id)

    return {
        "success": True,
        "message": "Proses transkripsi diulangi. Silakan cek status secara berkala.",
    }
