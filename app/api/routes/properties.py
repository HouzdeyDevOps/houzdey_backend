from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException, status
from typing import List, Optional
from fastapi.responses import JSONResponse, Response

from app.api.deps import get_current_user
from app.models.property import Property, PropertyUpdate, PropertyResponse, SortOrder, SortBy
from app.services.property_service import PropertyService
from app.core.dependencies import get_property_service
from app.utils.cloudinary_config import upload_image_to_cloudinary
import json

router = APIRouter()


@router.get("/users/me/properties")
async def get_user_properties(
    current_user: dict = Depends(get_current_user),
    property_service: PropertyService = Depends(get_property_service)
):
    """Get all properties owned by the current user"""
    try:
        properties = await property_service.get_user_properties(current_user["id"])
        return properties
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("", response_model=PropertyResponse)
async def get_properties(
    search: Optional[str] = None,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    property_type: Optional[str] = None,
    bedrooms: Optional[int] = Query(None, ge=0),
    bathrooms: Optional[int] = Query(None, ge=0),
    location_state: Optional[str] = None,
    location_area: Optional[str] = None,
    amenities: Optional[List[str]] = Query(None),
    listing_type: Optional[str] = Query(None),
    sort_by: SortBy = SortBy.CREATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=50),
    property_service: PropertyService = Depends(get_property_service)
):
    """Get properties with advanced filtering and pagination"""
    try:
        result = await property_service.get_properties_with_filters(
            search=search,
            min_price=min_price,
            max_price=max_price,
            property_type=property_type,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            location_state=location_state,
            location_area=location_area,
            amenities=amenities,
            listing_type=listing_type,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{property_id}")
async def get_property_by_id(
    property_id: str,
    property_service: PropertyService = Depends(get_property_service)
):
    """Get a property by ID with owner and reviews information"""
    try:
        property_obj = await property_service.get_property_by_id(property_id)
        return property_obj
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_property(
    title: str = Form(...),
    type: str = Form(...),
    price: float = Form(...),
    listing_type: str = Form(default="rent"),
    rental_price: Optional[float] = Form(None),
    sale_price: Optional[float] = Form(None),
    description: str = Form(...),
    amenities: str = Form(...),
    beds: int = Form(default=0),
    baths: int = Form(default=0),
    toilets: int = Form(default=0),
    condition: str = Form(...),
    furnishing: str = Form(...),
    address: str = Form(...),
    state: str = Form(...),
    lga: str = Form(...),
    ward: str = Form(...),
    estate: str = Form(None),
    size: str = Form(...),
    images: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    property_service: PropertyService = Depends(get_property_service)
):
    """Create a new property"""
    try:
        # Parse amenities from JSON string
        try:
            amenities_list = json.loads(amenities)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid amenities format"
            )
        
        # Upload images to Cloudinary
        image_urls = []
        for image in images:
            contents = await image.read()
            url = await upload_image_to_cloudinary(contents, "properties")
            image_urls.append(url)
        
        # Prepare property data
        property_data = {
            "title": title,
            "type": type,
            "price": price,
            "listing_type": listing_type,
            "rental_price": rental_price,
            "sale_price": sale_price,
            "description": description,
            "amenities": amenities_list,
            "images": image_urls,
            "beds": beds,
            "baths": baths,
            "toilets": toilets,
            "condition": condition,
            "furnishing": furnishing,
            "address": address,
            "state": state,
            "lga": lga,
            "ward": ward,
            "estate": estate,
            "size": size
        }
        
        # Create property using service
        result = await property_service.create_property(property_data, current_user["id"])
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create property: {str(e)}"
        )


@router.put("/{property_id}", response_model=Property)
async def update_property(
    property_id: str,
    property_update: PropertyUpdate,
    current_user: dict = Depends(get_current_user),
    property_service: PropertyService = Depends(get_property_service)
):
    """Update a property"""
    try:
        updated_property = await property_service.update_property(
            property_id, 
            property_update.dict(exclude_unset=True), 
            current_user["id"]
        )
        return Property(**updated_property)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: str,
    current_user: dict = Depends(get_current_user),
    property_service: PropertyService = Depends(get_property_service)
):
    """Delete a property"""
    try:
        await property_service.delete_property(property_id, current_user["id"])
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/{property_id}/status", status_code=status.HTTP_200_OK)
async def update_property_status(
    property_id: str,
    status_value: str = Form(..., alias="status"),
    current_user: dict = Depends(get_current_user),
    property_service: PropertyService = Depends(get_property_service)
):
    """Update property status"""
    try:
        result = await property_service.update_property_status(
            property_id, 
            status_value, 
            current_user["id"]
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )