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


# async def upload_image_to_cloudinary(file, folder="profile_pictures"):
#     try:
#         # Convert file to format Cloudinary can handle
#         result = uploader.upload(
#             file,
#             folder=folder,
#             resource_type="auto"
#         )
#         return result['secure_url']
#     except Exception as e:
#         raise Exception(f"Failed to upload image: {str(e)}") 