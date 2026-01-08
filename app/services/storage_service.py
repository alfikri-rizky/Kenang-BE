import mimetypes
import uuid
from datetime import timedelta
from typing import Optional

import aioboto3
import structlog
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import BusinessException

logger = structlog.get_logger(__name__)


class StorageService:
    def __init__(self):
        self.session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    async def generate_upload_url(
        self,
        file_name: str,
        content_type: str,
        folder: str = "uploads",
        max_size_mb: int = 10,
        expires_in_seconds: int = 3600,
    ) -> dict:
        file_extension = file_name.split(".")[-1] if "." in file_name else ""
        unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
        
        storage_key = f"{folder}/{unique_filename}"

        try:
            async with self.session.client("s3") as s3_client:
                presigned_post = await s3_client.generate_presigned_post(
                    Bucket=self.bucket_name,
                    Key=storage_key,
                    Fields={"Content-Type": content_type},
                    Conditions=[
                        {"Content-Type": content_type},
                        ["content-length-range", 1, max_size_mb * 1024 * 1024],
                    ],
                    ExpiresIn=expires_in_seconds,
                )

                logger.info(
                    "presigned_upload_url_generated",
                    storage_key=storage_key,
                    content_type=content_type,
                )

                return {
                    "upload_url": presigned_post["url"],
                    "fields": presigned_post["fields"],
                    "storage_key": storage_key,
                    "expires_in": expires_in_seconds,
                }

        except ClientError as e:
            logger.error("s3_presigned_url_error", error=str(e))
            raise BusinessException(
                code="S3_ERROR",
                message="Gagal membuat URL upload. Coba lagi.",
            )

    async def generate_download_url(
        self,
        storage_key: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        try:
            async with self.session.client("s3") as s3_client:
                url = await s3_client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": storage_key,
                    },
                    ExpiresIn=expires_in_seconds,
                )

                logger.info(
                    "presigned_download_url_generated",
                    storage_key=storage_key,
                )

                return url

        except ClientError as e:
            logger.error("s3_download_url_error", error=str(e), storage_key=storage_key)
            raise BusinessException(
                code="S3_ERROR",
                message="Gagal membuat URL download. Coba lagi.",
            )

    async def verify_file_exists(self, storage_key: str) -> bool:
        try:
            async with self.session.client("s3") as s3_client:
                await s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=storage_key,
                )
                return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error("s3_verify_error", error=str(e), storage_key=storage_key)
            return False

    async def get_file_metadata(self, storage_key: str) -> Optional[dict]:
        try:
            async with self.session.client("s3") as s3_client:
                response = await s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=storage_key,
                )

                return {
                    "content_type": response.get("ContentType"),
                    "content_length": response.get("ContentLength"),
                    "last_modified": response.get("LastModified"),
                    "etag": response.get("ETag"),
                }

        except ClientError as e:
            logger.error("s3_metadata_error", error=str(e), storage_key=storage_key)
            return None

    async def delete_file(self, storage_key: str) -> bool:
        try:
            async with self.session.client("s3") as s3_client:
                await s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=storage_key,
                )

                logger.info("s3_file_deleted", storage_key=storage_key)
                return True

        except ClientError as e:
            logger.error("s3_delete_error", error=str(e), storage_key=storage_key)
            return False

    async def copy_file(
        self,
        source_key: str,
        destination_key: str,
    ) -> bool:
        try:
            async with self.session.client("s3") as s3_client:
                await s3_client.copy_object(
                    Bucket=self.bucket_name,
                    CopySource={"Bucket": self.bucket_name, "Key": source_key},
                    Key=destination_key,
                )

                logger.info(
                    "s3_file_copied",
                    source_key=source_key,
                    destination_key=destination_key,
                )
                return True

        except ClientError as e:
            logger.error("s3_copy_error", error=str(e))
            return False

    def get_public_url(self, storage_key: str) -> str:
        return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{storage_key}"

    def get_cloudfront_url(self, storage_key: str) -> Optional[str]:
        if hasattr(settings, "CLOUDFRONT_DOMAIN") and settings.CLOUDFRONT_DOMAIN:
            return f"https://{settings.CLOUDFRONT_DOMAIN}/{storage_key}"
        return None

    @staticmethod
    def validate_content_type(content_type: str, allowed_types: list[str]) -> bool:
        return content_type in allowed_types

    @staticmethod
    def get_folder_for_type(file_type: str) -> str:
        folders = {
            "photo": "photos",
            "audio": "audio",
            "video": "videos",
            "document": "documents",
            "avatar": "avatars",
        }
        return folders.get(file_type, "uploads")

    @staticmethod
    def get_allowed_image_types() -> list[str]:
        return [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/heic",
            "image/heif",
            "image/webp",
        ]

    @staticmethod
    def get_allowed_audio_types() -> list[str]:
        return [
            "audio/mpeg",
            "audio/mp3",
            "audio/wav",
            "audio/aac",
            "audio/m4a",
            "audio/ogg",
        ]

    @staticmethod
    def get_allowed_video_types() -> list[str]:
        return [
            "video/mp4",
            "video/quicktime",
            "video/x-msvideo",
            "video/webm",
        ]
