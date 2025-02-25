import cloudinary # type: ignore
import cloudinary.uploader # type: ignore
from app.core.config import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

async def upload_image_to_cloudinary(file_content: bytes, folder: str) -> str:
    """Upload image to Cloudinary and return the URL"""
    result = cloudinary.uploader.upload(
        file_content,
        folder=folder
    )
    return result['secure_url']


async def delete_image_from_cloudinary(public_id: str) -> None:
    try:
        cloudinary.uploader.destroy(public_id)
        return True
    except Exception as e:
        raise Exception("Failed to delete image from cloud storage")


