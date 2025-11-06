import cloudinary # type: ignore
import cloudinary.uploader # type: ignore
from app.core.config import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

# Project-specific folder prefix to organize files across multiple projects
PROJECT_PREFIX = "houzdey"  # Change this to your project identifier

async def upload_image_to_cloudinary(file_content: bytes, folder: str) -> str:
    """
    Upload image to Cloudinary in a project-specific folder structure
    
    Args:
        file_content: Image bytes
        folder: Subfolder name (e.g., 'profile_pictures', 'properties')
    
    Returns:
        Secure HTTPS URL of uploaded image
    
    Example folder structure in Cloudinary:
        houzdey/profile_pictures/abc123.jpg
        houzdey/properties/xyz789.jpg
    """
    # Prefix folder with project name for organization
    organized_folder = f"{PROJECT_PREFIX}/{folder}"
    
    result = cloudinary.uploader.upload(
        file_content,
        folder=organized_folder
    )
    return result['secure_url']


async def upload_video_to_cloudinary(file_content: bytes, folder: str) -> str:
    """
    Upload video to Cloudinary in a project-specific folder structure
    
    Args:
        file_content: Video bytes
        folder: Subfolder name (e.g., 'properties')
    
    Returns:
        Secure HTTPS URL of uploaded video
    
    Example folder structure in Cloudinary:
        houzdey/properties/videos/abc123.mp4
    """
    # Prefix folder with project name for organization
    organized_folder = f"{PROJECT_PREFIX}/{folder}/videos"
    
    result = cloudinary.uploader.upload(
        file_content,
        folder=organized_folder,
        resource_type="video",
        eager=[
            {"quality": "auto", "fetch_format": "auto"}
        ],
        eager_async=True
    )
    return result['secure_url']


def extract_public_id_from_url(cloudinary_url: str) -> str:
    """
    Extract public_id from Cloudinary URL
    Example URL: https://res.cloudinary.com/cloud_name/image/upload/v1234567890/folder/image_name.jpg
    Returns: folder/image_name
    """
    try:
        # Split by '/' and find the part after 'upload/'
        parts = cloudinary_url.split('/')
        upload_index = parts.index('upload')
        
        # Skip version number if present (starts with 'v' followed by digits)
        start_index = upload_index + 1
        if start_index < len(parts) and parts[start_index].startswith('v') and parts[start_index][1:].isdigit():
            start_index += 1
        
        # Join remaining parts (folder/filename) and remove file extension
        public_id_parts = parts[start_index:]
        public_id = '/'.join(public_id_parts)
        
        # Remove file extension
        if '.' in public_id:
            public_id = public_id.rsplit('.', 1)[0]
        
        return public_id
    except Exception as e:
        # Fallback to simple extraction
        return cloudinary_url.split("/")[-1].split(".")[0]

async def delete_image_from_cloudinary(public_id: str) -> bool:
    """Delete image from Cloudinary"""
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        print(f"Failed to delete image with public_id {public_id}: {str(e)}")
        return False


