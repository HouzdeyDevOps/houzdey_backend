from fastapi import APIRouter, Depends, UploadFile, Form
from app.services.upload import UploadService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/")
async def upload_file(
    file: UploadFile,
    type: str = Form(...),
    context: str = Form("chat"),  # Default to 'chat' for backward compatibility
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Upload a file (image or voice message) and return its public URL
    
    Args:
        file: The file to upload
        type: File type ('image' or 'voice')
        context: Upload context ('chat', 'blog', 'profile', etc.)
    """
    # Handle both User object and dict
    user_id = current_user.get("id") or str(current_user.get("_id")) if isinstance(current_user, dict) else current_user.id
    file_url = await UploadService.upload_file(file, type, user_id, context)
    return {"file_url": file_url} 