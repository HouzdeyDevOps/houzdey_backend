from typing import Optional
from fastapi import UploadFile, HTTPException
import cloudinary  # type: ignore
import cloudinary.uploader  # type: ignore
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)


def _sniff_content_type(header: bytes) -> Optional[str]:
    """Identify a file's real type from its leading bytes, ignoring the client-supplied Content-Type header."""
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "image/gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        return "audio/wav"
    if header.startswith(b"OggS"):
        return "audio/ogg"
    if header.startswith(b"\x1aE\xdf\xa3"):
        return "audio/webm"
    if header.startswith(b"ID3") or header[:2] in (b"\xff\xfb", b"\xff\xfa", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mp3"
    return None


class UploadService:
    @staticmethod
    async def upload_file(
        file: UploadFile,
        file_type: str,
        user_id: str,
        context: str = "chat"
    ) -> str:
        try:
            if file_type not in ['image', 'voice']:
                raise HTTPException(status_code=400, detail="Invalid file type")

            allowed_types = settings.ALLOWED_IMAGE_TYPES if file_type == 'image' else settings.ALLOWED_AUDIO_TYPES

            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid {file_type} type. Allowed: {', '.join(allowed_types)}"
                )

            contents = await file.read()

            if len(contents) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB size limit"
                )

            sniffed_type = _sniff_content_type(contents[:16])
            if sniffed_type is None or sniffed_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"File content does not match a supported {file_type} format"
                )

            folder_path = f"{context}/{file_type}/{user_id}" if context == "chat" else f"{context}/{file_type}"

            upload_result = cloudinary.uploader.upload(
                contents,
                folder=folder_path,
                resource_type="auto",
                public_id=None,
                overwrite=False,
                access_mode="public",
                tags=[f"user_{user_id}", file_type, context]
            )

            return upload_result['secure_url']

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise HTTPException(status_code=500, detail="File upload failed. Please try again.")
