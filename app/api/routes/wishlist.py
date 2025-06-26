from fastapi import APIRouter, Depends, HTTPException
from app.crud import add_to_wishlist, get_user_wishlist, remove_from_wishlist, get_wishlist_ids
from app.api.deps import get_current_user
from pydantic import BaseModel


class WishlistAdd(BaseModel):
    property_id: str


router = APIRouter()


@router.post("")
async def add_wishlist(
    wishlist_data: WishlistAdd, current_user=Depends(get_current_user)
):
    try:
        await add_to_wishlist(current_user.id, wishlist_data.property_id)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{property_id}")
async def remove_wishlist(property_id: str, current_user=Depends(get_current_user)):
    success = await remove_from_wishlist(current_user.id, property_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove from wishlist")
    return {"message": "Removed from wishlist"}


@router.get("")
async def get_from_wishlist(current_user=Depends(get_current_user)):
    """Get user's wishlist with full property details"""
    items = await get_user_wishlist(current_user.id)
    return {"items": items}

@router.get("/ids")
async def get_wishlist_property_ids(current_user=Depends(get_current_user)):
    """Get user's wishlist property IDs only"""
    property_ids = await get_wishlist_ids(current_user.id)
    return {"items": property_ids}
