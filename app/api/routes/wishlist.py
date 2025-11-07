from fastapi import APIRouter, Depends, HTTPException
from app.services.user_service import UserService
from app.services.property_service import PropertyService
from app.core.dependencies import get_user_service, get_property_service
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
async def get_from_wishlist(
    current_user=Depends(get_current_user),
    property_service: PropertyService = Depends(get_property_service)
):
    """Get user's wishlist with full property details"""
    try:
        wishlist_property_ids = current_user.get("wishlist", [])
        
        if not wishlist_property_ids:
            return {"items": []}
        
        # Fetch full property details for each property in wishlist
        properties = []
        for property_id in wishlist_property_ids:
            try:
                property_data = await property_service.get_property_by_id(property_id)
                if property_data:
                    properties.append(property_data)
            except Exception as e:
                print(f"Error fetching property {property_id}: {str(e)}")
                continue
        
        return {"items": properties}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ids")
async def get_wishlist_property_ids(current_user=Depends(get_current_user)):
    """Get user's wishlist property IDs only"""
    return {"items": current_user.get("wishlist", [])}
