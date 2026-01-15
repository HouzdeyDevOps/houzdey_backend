from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException, status, Header
from typing import List, Optional
from fastapi.responses import JSONResponse, Response

from app.api.deps import get_current_user
from app.models.property import Property, PropertyUpdate, PropertyResponse, SortOrder, SortBy, PropertyImport, PropertyImportResponse
from app.services.property_service import PropertyService
from app.core.dependencies import get_property_service
from app.utils.cloudinary_config import upload_image_to_cloudinary, upload_video_to_cloudinary
from app.core.config import settings
import json

router = APIRouter()


@router.post("/import", response_model=PropertyImportResponse, status_code=status.HTTP_201_CREATED)
async def import_property(
    property_data: PropertyImport,
    x_scraper_source: Optional[str] = Header(None, alias="X-Scraper-Source"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    property_service: PropertyService = Depends(get_property_service)
):
    """
    Import a property from an external source (e.g., n8n scraper).

    This endpoint is designed for automated property imports and accepts:
    - JSON body with property details
    - Image URLs (will be downloaded and uploaded to Cloudinary)
    - Source tracking information

    Authentication: Requires X-API-Key header matching SCRAPER_API_KEY env var,
    or standard Bearer token authentication.
    """
    try:
        # Validate API key for scraper access
        scraper_api_key = getattr(settings, 'SCRAPER_API_KEY', None)
        if scraper_api_key and x_api_key != scraper_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key for scraper access"
            )

        # Get the scraper bot owner ID from settings or use a default
        owner_id = getattr(settings, 'SCRAPER_BOT_USER_ID', None)
        if not owner_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SCRAPER_BOT_USER_ID not configured. Please set this in your environment."
            )

        # Convert Pydantic model to dict
        import_dict = property_data.model_dump()
        

        # Override source if provided in header
        if x_scraper_source:
            import_dict["source"] = x_scraper_source

        # Import the property
        result = await property_service.import_property(import_dict, owner_id)

        return PropertyImportResponse(
            success=result["success"],
            message=result["message"],
            property_id=result.get("property_id"),
            property_slug=result.get("property_slug")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import property: {str(e)}"
        )


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


@router.get("/slug/{slug:path}")
async def get_property_by_slug(
    slug: str,
    property_service: PropertyService = Depends(get_property_service)
):
    """Get a property by SEO-friendly slug with owner and reviews information"""
    try:
        property_obj = await property_service.get_property_by_slug(slug)
        return property_obj
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{property_id}")
async def get_property_by_id(
    property_id: str,
    property_service: PropertyService = Depends(get_property_service)
):
    """Get a property by ID with owner and reviews information (legacy support)"""
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
    agency_fee: Optional[float] = Form(None),
    legal_fee: Optional[float] = Form(None),
    other_fees: Optional[float] = Form(None),
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
    size: str = Form(None),
    property_status: str = Form(default="available", alias="status"),
    images: List[UploadFile] = File(...),
    video: Optional[UploadFile] = File(None),
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
        
        # Upload video to Cloudinary (optional)
        video_url = None
        if video:
            video_contents = await video.read()
            video_url = await upload_video_to_cloudinary(video_contents, "properties")
        
        # Prepare property data
        property_data = {
            "title": title,
            "type": type,
            "price": price,
            "listing_type": listing_type,
            "rental_price": rental_price,
            "sale_price": sale_price,
            "agency_fee": agency_fee,
            "legal_fee": legal_fee,
            "other_fees": other_fees,
            "description": description,
            "amenities": amenities_list,
            "images": image_urls,
            "video": video_url,
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
            "size": size,
            "status": property_status
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


@router.put("/{property_id}")
async def update_property(
    property_id: str,
    title: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    listing_type: Optional[str] = Form(None),
    rental_price: Optional[float] = Form(None),
    sale_price: Optional[float] = Form(None),
    agency_fee: Optional[float] = Form(None),
    legal_fee: Optional[float] = Form(None),
    other_fees: Optional[float] = Form(None),
    description: Optional[str] = Form(None),
    amenities: Optional[str] = Form(None),
    beds: Optional[int] = Form(None),
    baths: Optional[int] = Form(None),
    toilets: Optional[int] = Form(None),
    condition: Optional[str] = Form(None),
    furnishing: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    lga: Optional[str] = Form(None),
    ward: Optional[str] = Form(None),
    estate: Optional[str] = Form(None),
    size: Optional[str] = Form(None),
    property_status: Optional[str] = Form(None, alias="status"),
    images: Optional[List[UploadFile]] = File(None),
    video: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    property_service: PropertyService = Depends(get_property_service)
):
    """Update a property"""
    try:
        # Build update data only with provided fields
        update_data = {}
        
        if title is not None:
            update_data["title"] = title
        if type is not None:
            update_data["type"] = type
        if price is not None:
            update_data["price"] = price
        if listing_type is not None:
            update_data["listing_type"] = listing_type
        if rental_price is not None:
            update_data["rental_price"] = rental_price
        if sale_price is not None:
            update_data["sale_price"] = sale_price
        if agency_fee is not None:
            update_data["agency_fee"] = agency_fee
        if legal_fee is not None:
            update_data["legal_fee"] = legal_fee
        if other_fees is not None:
            update_data["other_fees"] = other_fees
        if description is not None:
            update_data["description"] = description
        if beds is not None:
            update_data["beds"] = beds
        if baths is not None:
            update_data["baths"] = baths
        if toilets is not None:
            update_data["toilets"] = toilets
        if condition is not None:
            update_data["condition"] = condition
        if furnishing is not None:
            update_data["furnishing"] = furnishing
        if address is not None:
            update_data["address"] = address
        if state is not None:
            update_data["state"] = state
        if lga is not None:
            update_data["lga"] = lga
        if ward is not None:
            update_data["ward"] = ward
        if estate is not None:
            update_data["estate"] = estate
        if size is not None:
            update_data["size"] = size
        if property_status is not None:
            update_data["status"] = property_status
            
        # Parse amenities if provided
        if amenities is not None:
            try:
                update_data["amenities"] = json.loads(amenities)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid amenities format"
                )
        
        # Handle new images if provided
        if images:
            image_urls = []
            for image in images:
                contents = await image.read()
                url = await upload_image_to_cloudinary(contents, "properties")
                image_urls.append(url)
            update_data["images"] = image_urls
        
        # Handle new video if provided
        if video:
            video_contents = await video.read()
            video_url = await upload_video_to_cloudinary(video_contents, "properties")
            update_data["video"] = video_url
        
        # Update property using service
        updated_property = await property_service.update_property(
            property_id, 
            update_data, 
            current_user["id"]
        )
        return updated_property
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update property: {str(e)}"
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