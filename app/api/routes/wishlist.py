from fastapi import APIRouter, Depends, HTTPException
from app.services.user_service import UserService
from app.core.dependencies import get_user_service
from app.api.deps import get_current_user
from pydantic import BaseModel


class WishlistAdd(BaseModel):
    property_id: str


router = APIRouter()


@router.post("")
async def add_wishlist(
    wishlist_data: WishlistAdd, 
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    try:
        result = await user_service.add_to_wishlist(
            current_user["id"], 
            wishlist_data.property_id, 
            current_user["id"]
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{property_id}")
async def remove_wishlist(
    property_id: str, 
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    try:
        result = await user_service.remove_from_wishlist(
            current_user["id"], 
            property_id, 
            current_user["id"]
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_from_wishlist(current_user=Depends(get_current_user)):
    """Get user's wishlist with full property details"""
    # For now, return basic wishlist - this would need property service integration
    return {"items": current_user.get("wishlist", [])}

@router.get("/ids")
async def get_wishlist_property_ids(current_user=Depends(get_current_user)):
    """Get user's wishlist property IDs only"""
    return {"items": current_user.get("wishlist", [])}
