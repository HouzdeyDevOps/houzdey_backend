from fastapi import APIRouter, Depends, UploadFile, Form
from app.services.upload import UploadService
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/")
async def upload_file(
    file: UploadFile,
    type: str = Form(...),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Upload a file (image or voice message) and return its public URL
    """
    file_url = await UploadService.upload_file(file, type, current_user.id)
    return {"file_url": file_url} 