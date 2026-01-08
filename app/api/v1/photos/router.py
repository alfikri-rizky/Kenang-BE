from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.photos.schemas import (
    ConfirmPhotoUploadRequest,
    PhotoListResponse,
    PhotoResponse,
    UpdatePhotoRequest,
    UploadAudioRequest,
    UploadAudioResponse,
    UploadPhotoRequest,
    UploadPhotoResponse,
)
from app.core.exceptions import BusinessException, NotFoundException
from app.db.models import Photo, User
from app.services.circle_service import CircleService
from app.services.storage_service import StorageService
from app.utils.file_utils import FileValidator

router = APIRouter()


@router.post(
    "/upload-url",
    response_model=UploadPhotoResponse,
    status_code=status.HTTP_200_OK,
    summary="Dapatkan URL untuk upload foto",
    description="Menghasilkan presigned URL untuk upload foto ke S3.",
)
async def get_photo_upload_url(
    request: UploadPhotoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadPhotoResponse:
    circle_service = CircleService(db)
    await circle_service._check_access(
        request.circle_id, current_user.id, required_role="contributor"
    )

    if not FileValidator.is_valid_image_extension(request.filename):
        raise BusinessException(
            code="INVALID_FILE_TYPE",
            message="Format file tidak didukung. Gunakan JPG, PNG, HEIC, atau WebP.",
        )

    storage_service = StorageService()

    allowed_types = storage_service.get_allowed_image_types()
    if not storage_service.validate_content_type(request.content_type, allowed_types):
        raise BusinessException(
            code="INVALID_CONTENT_TYPE",
            message="Content type tidak valid untuk foto.",
        )

    folder = f"photos/{request.circle_id}"

    upload_data = await storage_service.generate_upload_url(
        file_name=request.filename,
        content_type=request.content_type,
        folder=folder,
        max_size_mb=FileValidator.MAX_IMAGE_SIZE_MB,
    )

    return UploadPhotoResponse(**upload_data)


@router.post(
    "/confirm",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Konfirmasi upload foto",
    description="Mengkonfirmasi bahwa foto sudah berhasil diupload ke S3 dan membuat record di database.",
)
async def confirm_photo_upload(
    request: ConfirmPhotoUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoResponse:
    circle_service = CircleService(db)
    await circle_service._check_access(
        request.circle_id, current_user.id, required_role="contributor"
    )

    storage_service = StorageService()

    file_exists = await storage_service.verify_file_exists(request.storage_key)
    if not file_exists:
        raise NotFoundException(
            "File tidak ditemukan di storage. Upload mungkin gagal."
        )

    metadata = await storage_service.get_file_metadata(request.storage_key)

    photo = Photo(
        circle_id=request.circle_id,
        uploaded_by=current_user.id,
        storage_key=request.storage_key,
        mime_type=metadata.get("content_type") if metadata else None,
        file_size_bytes=metadata.get("content_length") if metadata else None,
        caption=request.caption,
        taken_at=request.taken_at,
    )

    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    download_url = await storage_service.generate_download_url(request.storage_key)

    return PhotoResponse(
        id=photo.id,
        circle_id=photo.circle_id,
        storage_key=photo.storage_key,
        thumbnail_key=photo.thumbnail_key,
        url=download_url,
        thumbnail_url=None,
        original_filename=photo.original_filename,
        file_size_bytes=photo.file_size_bytes,
        mime_type=photo.mime_type,
        width=photo.width,
        height=photo.height,
        taken_at=photo.taken_at,
        caption=photo.caption,
        uploaded_by=photo.uploaded_by,
        created_at=photo.created_at,
    )


@router.get(
    "",
    response_model=PhotoListResponse,
    status_code=status.HTTP_200_OK,
    summary="Dapatkan daftar foto dalam lingkaran",
)
async def get_photos(
    circle_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoListResponse:
    circle_service = CircleService(db)
    await circle_service._check_access(circle_id, current_user.id)

    query = (
        select(Photo)
        .where(Photo.circle_id == circle_id, Photo.deleted_at.is_(None))
        .order_by(Photo.taken_at.desc().nulls_last(), Photo.created_at.desc())
    )
    result = await db.execute(query)
    photos = list(result.scalars().all())

    storage_service = StorageService()
    photo_responses = []

    for photo in photos:
        url = await storage_service.generate_download_url(photo.storage_key)
        thumbnail_url = (
            await storage_service.generate_download_url(photo.thumbnail_key)
            if photo.thumbnail_key
            else None
        )

        photo_responses.append(
            PhotoResponse(
                id=photo.id,
                circle_id=photo.circle_id,
                storage_key=photo.storage_key,
                thumbnail_key=photo.thumbnail_key,
                url=url,
                thumbnail_url=thumbnail_url,
                original_filename=photo.original_filename,
                file_size_bytes=photo.file_size_bytes,
                mime_type=photo.mime_type,
                width=photo.width,
                height=photo.height,
                taken_at=photo.taken_at,
                caption=photo.caption,
                uploaded_by=photo.uploaded_by,
                created_at=photo.created_at,
            )
        )

    return PhotoListResponse(photos=photo_responses, total=len(photo_responses))


@router.get(
    "/{photo_id}",
    response_model=PhotoResponse,
    status_code=status.HTTP_200_OK,
    summary="Dapatkan detail foto",
)
async def get_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoResponse:
    query = select(Photo).where(Photo.id == photo_id, Photo.deleted_at.is_(None))
    result = await db.execute(query)
    photo = result.scalar_one_or_none()

    if not photo:
        raise NotFoundException("Foto tidak ditemukan")

    circle_service = CircleService(db)
    await circle_service._check_access(photo.circle_id, current_user.id)

    storage_service = StorageService()
    url = await storage_service.generate_download_url(photo.storage_key)
    thumbnail_url = (
        await storage_service.generate_download_url(photo.thumbnail_key)
        if photo.thumbnail_key
        else None
    )

    return PhotoResponse(
        id=photo.id,
        circle_id=photo.circle_id,
        storage_key=photo.storage_key,
        thumbnail_key=photo.thumbnail_key,
        url=url,
        thumbnail_url=thumbnail_url,
        original_filename=photo.original_filename,
        file_size_bytes=photo.file_size_bytes,
        mime_type=photo.mime_type,
        width=photo.width,
        height=photo.height,
        taken_at=photo.taken_at,
        caption=photo.caption,
        uploaded_by=photo.uploaded_by,
        created_at=photo.created_at,
    )


@router.patch(
    "/{photo_id}",
    response_model=PhotoResponse,
    status_code=status.HTTP_200_OK,
    summary="Update metadata foto",
)
async def update_photo(
    photo_id: str,
    request: UpdatePhotoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoResponse:
    query = select(Photo).where(Photo.id == photo_id, Photo.deleted_at.is_(None))
    result = await db.execute(query)
    photo = result.scalar_one_or_none()

    if not photo:
        raise NotFoundException("Foto tidak ditemukan")

    circle_service = CircleService(db)
    await circle_service._check_access(
        photo.circle_id, current_user.id, required_role="contributor"
    )

    if request.caption is not None:
        photo.caption = request.caption
    if request.taken_at is not None:
        photo.taken_at = request.taken_at

    photo.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(photo)

    storage_service = StorageService()
    url = await storage_service.generate_download_url(photo.storage_key)
    thumbnail_url = (
        await storage_service.generate_download_url(photo.thumbnail_key)
        if photo.thumbnail_key
        else None
    )

    return PhotoResponse(
        id=photo.id,
        circle_id=photo.circle_id,
        storage_key=photo.storage_key,
        thumbnail_key=photo.thumbnail_key,
        url=url,
        thumbnail_url=thumbnail_url,
        original_filename=photo.original_filename,
        file_size_bytes=photo.file_size_bytes,
        mime_type=photo.mime_type,
        width=photo.width,
        height=photo.height,
        taken_at=photo.taken_at,
        caption=photo.caption,
        uploaded_by=photo.uploaded_by,
        created_at=photo.created_at,
    )


@router.delete(
    "/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus foto",
)
async def delete_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    query = select(Photo).where(Photo.id == photo_id, Photo.deleted_at.is_(None))
    result = await db.execute(query)
    photo = result.scalar_one_or_none()

    if not photo:
        raise NotFoundException("Foto tidak ditemukan")

    circle_service = CircleService(db)
    await circle_service._check_access(
        photo.circle_id, current_user.id, required_role="contributor"
    )

    photo.deleted_at = datetime.utcnow()
    await db.commit()


@router.post(
    "/audio/upload-url",
    response_model=UploadAudioResponse,
    status_code=status.HTTP_200_OK,
    summary="Dapatkan URL untuk upload audio",
    description="Menghasilkan presigned URL untuk upload audio (cerita) ke S3.",
)
async def get_audio_upload_url(
    request: UploadAudioRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadAudioResponse:
    circle_service = CircleService(db)
    await circle_service._check_access(
        request.circle_id, current_user.id, required_role="contributor"
    )

    if not FileValidator.is_valid_audio_extension(request.filename):
        raise BusinessException(
            code="INVALID_FILE_TYPE",
            message="Format audio tidak didukung. Gunakan MP3, WAV, AAC, M4A, atau OGG.",
        )

    storage_service = StorageService()

    allowed_types = storage_service.get_allowed_audio_types()
    if not storage_service.validate_content_type(request.content_type, allowed_types):
        raise BusinessException(
            code="INVALID_CONTENT_TYPE",
            message="Content type tidak valid untuk audio.",
        )

    folder = f"audio/{request.circle_id}"

    upload_data = await storage_service.generate_upload_url(
        file_name=request.filename,
        content_type=request.content_type,
        folder=folder,
        max_size_mb=FileValidator.MAX_AUDIO_SIZE_MB,
    )

    return UploadAudioResponse(**upload_data)
