from fastapi import UploadFile, HTTPException
import cloudinary # type: ignore
import cloudinary.uploader # type: ignore
from app.core.config import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

class UploadService:
    @staticmethod
    async def upload_file(
        file: UploadFile,
        file_type: str,
        user_id: str,
        context: str = "chat"  # Can be 'chat', 'blog', 'profile', etc.
    ) -> str:
        try:
            # Validate file type
            if file_type not in ['image', 'voice']:
                raise HTTPException(status_code=400, detail="Invalid file type")

            # Validate content type
            if file_type == 'image' and file.content_type not in settings.ALLOWED_IMAGE_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid image type. Allowed: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
                )
            elif file_type == 'voice' and file.content_type not in settings.ALLOWED_AUDIO_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid audio type. Allowed: {', '.join(settings.ALLOWED_AUDIO_TYPES)}"
                )

            # Read file content
            contents = await file.read()

            # Upload to Cloudinary with dynamic folder structure
            folder_path = f"{context}/{file_type}/{user_id}" if context == "chat" else f"{context}/{file_type}"
            
            upload_result = cloudinary.uploader.upload(
                contents,
                folder=folder_path,
                resource_type="auto",
                public_id=None,  # Let Cloudinary generate a unique name
                overwrite=False,
                access_mode="public",
                tags=[f"user_{user_id}", file_type, context]
            )

            # Return the secure URL
            return upload_result['secure_url']

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) 