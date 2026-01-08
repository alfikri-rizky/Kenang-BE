import mimetypes
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image


class FileValidator:
    MAX_IMAGE_SIZE_MB = 10
    MAX_AUDIO_SIZE_MB = 50
    MAX_VIDEO_SIZE_MB = 100

    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
    ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".ogg"}
    ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}

    @staticmethod
    def validate_file_size(file_size_bytes: int, max_size_mb: int) -> bool:
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size_bytes <= max_size_bytes

    @staticmethod
    def validate_image_size(file_size_bytes: int) -> bool:
        return FileValidator.validate_file_size(
            file_size_bytes, FileValidator.MAX_IMAGE_SIZE_MB
        )

    @staticmethod
    def validate_audio_size(file_size_bytes: int) -> bool:
        return FileValidator.validate_file_size(
            file_size_bytes, FileValidator.MAX_AUDIO_SIZE_MB
        )

    @staticmethod
    def validate_video_size(file_size_bytes: int) -> bool:
        return FileValidator.validate_file_size(
            file_size_bytes, FileValidator.MAX_VIDEO_SIZE_MB
        )

    @staticmethod
    def get_file_extension(filename: str) -> str:
        return filename.lower().split(".")[-1] if "." in filename else ""

    @staticmethod
    def is_valid_image_extension(filename: str) -> bool:
        ext = f".{FileValidator.get_file_extension(filename)}"
        return ext in FileValidator.ALLOWED_IMAGE_EXTENSIONS

    @staticmethod
    def is_valid_audio_extension(filename: str) -> bool:
        ext = f".{FileValidator.get_file_extension(filename)}"
        return ext in FileValidator.ALLOWED_AUDIO_EXTENSIONS

    @staticmethod
    def is_valid_video_extension(filename: str) -> bool:
        ext = f".{FileValidator.get_file_extension(filename)}"
        return ext in FileValidator.ALLOWED_VIDEO_EXTENSIONS

    @staticmethod
    def guess_content_type(filename: str) -> str:
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"


class ImageProcessor:
    MAX_DIMENSION = 4096
    THUMBNAIL_SIZE = (400, 400)
    JPEG_QUALITY = 85

    @staticmethod
    def compress_image(
        image_bytes: bytes,
        max_size_mb: float = 2.0,
        quality: int = 85,
    ) -> bytes:
        try:
            img = Image.open(BytesIO(image_bytes))

            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background

            max_dimension = ImageProcessor.MAX_DIMENSION
            if img.width > max_dimension or img.height > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

            output = BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            compressed_bytes = output.getvalue()

            max_size_bytes = int(max_size_mb * 1024 * 1024)
            current_quality = quality

            while len(compressed_bytes) > max_size_bytes and current_quality > 50:
                current_quality -= 5
                output = BytesIO()
                img.save(output, format="JPEG", quality=current_quality, optimize=True)
                compressed_bytes = output.getvalue()

            return compressed_bytes

        except Exception as e:
            raise ValueError(f"Gagal memproses gambar: {str(e)}")

    @staticmethod
    def create_thumbnail(
        image_bytes: bytes,
        size: Tuple[int, int] = None,
    ) -> bytes:
        try:
            if size is None:
                size = ImageProcessor.THUMBNAIL_SIZE

            img = Image.open(BytesIO(image_bytes))

            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background

            img.thumbnail(size, Image.Resampling.LANCZOS)

            output = BytesIO()
            img.save(output, format="JPEG", quality=80, optimize=True)

            return output.getvalue()

        except Exception as e:
            raise ValueError(f"Gagal membuat thumbnail: {str(e)}")

    @staticmethod
    def get_image_dimensions(image_bytes: bytes) -> Optional[Tuple[int, int]]:
        try:
            img = Image.open(BytesIO(image_bytes))
            return img.size
        except Exception:
            return None

    @staticmethod
    def extract_exif_data(image_bytes: bytes) -> dict:
        try:
            from PIL.ExifTags import TAGS

            img = Image.open(BytesIO(image_bytes))
            exif_data = {}

            if hasattr(img, "_getexif") and img._getexif():
                exif = img._getexif()
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = str(value)

            return exif_data

        except Exception:
            return {}


class FileHasher:
    @staticmethod
    def calculate_hash(file_bytes: bytes) -> str:
        import hashlib
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def calculate_md5(file_bytes: bytes) -> str:
        import hashlib
        return hashlib.md5(file_bytes).hexdigest()
