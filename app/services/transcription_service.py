import tempfile
from pathlib import Path
from typing import Optional

import httpx
import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.services.storage_service import StorageService

logger = structlog.get_logger(__name__)


class TranscriptionService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.storage_service = StorageService()

    async def transcribe_audio(
        self,
        audio_storage_key: str,
        language: str = "id",
    ) -> str:
        if not settings.OPENAI_API_KEY:
            raise BusinessException(
                code="OPENAI_NOT_CONFIGURED",
                message="Layanan transkripsi tidak tersedia saat ini.",
            )

        temp_file_path = None
        try:
            audio_url = await self.storage_service.generate_download_url(
                audio_storage_key, expires_in_seconds=300
            )

            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(audio_url, follow_redirects=True)
                response.raise_for_status()
                audio_data = response.content

            extension = Path(audio_storage_key).suffix or ".mp3"
            with tempfile.NamedTemporaryFile(
                suffix=extension, delete=False
            ) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            with open(temp_file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="text",
                )

            logger.info(
                "audio_transcribed",
                storage_key=audio_storage_key,
                language=language,
                transcript_length=len(transcript),
            )

            return transcript

        except httpx.HTTPError as e:
            logger.error(
                "audio_download_failed",
                storage_key=audio_storage_key,
                error=str(e),
            )
            raise BusinessException(
                code="AUDIO_DOWNLOAD_FAILED",
                message="Gagal mengunduh audio untuk transkripsi.",
            )

        except Exception as e:
            logger.error(
                "transcription_failed",
                storage_key=audio_storage_key,
                error=str(e),
            )
            raise BusinessException(
                code="TRANSCRIPTION_FAILED",
                message="Gagal mentranskrip audio. Silakan coba lagi.",
            )

        finally:
            if temp_file_path:
                try:
                    Path(temp_file_path).unlink(missing_ok=True)
                except Exception:
                    pass

    async def transcribe_with_timestamps(
        self,
        audio_storage_key: str,
        language: str = "id",
    ) -> dict:
        if not settings.OPENAI_API_KEY:
            raise BusinessException(
                code="OPENAI_NOT_CONFIGURED",
                message="Layanan transkripsi tidak tersedia saat ini.",
            )

        temp_file_path = None
        try:
            audio_url = await self.storage_service.generate_download_url(
                audio_storage_key, expires_in_seconds=300
            )

            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(audio_url, follow_redirects=True)
                response.raise_for_status()
                audio_data = response.content

            extension = Path(audio_storage_key).suffix or ".mp3"
            with tempfile.NamedTemporaryFile(
                suffix=extension, delete=False
            ) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            with open(temp_file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )

            logger.info(
                "audio_transcribed_with_timestamps",
                storage_key=audio_storage_key,
                language=language,
            )

            return {
                "text": transcript.text,
                "segments": [
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text,
                    }
                    for segment in (transcript.segments or [])
                ],
                "duration": transcript.duration,
            }

        except httpx.HTTPError as e:
            logger.error(
                "audio_download_failed",
                storage_key=audio_storage_key,
                error=str(e),
            )
            raise BusinessException(
                code="AUDIO_DOWNLOAD_FAILED",
                message="Gagal mengunduh audio untuk transkripsi.",
            )

        except Exception as e:
            logger.error(
                "transcription_failed",
                storage_key=audio_storage_key,
                error=str(e),
            )
            raise BusinessException(
                code="TRANSCRIPTION_FAILED",
                message="Gagal mentranskrip audio. Silakan coba lagi.",
            )

        finally:
            if temp_file_path:
                try:
                    Path(temp_file_path).unlink(missing_ok=True)
                except Exception:
                    pass
