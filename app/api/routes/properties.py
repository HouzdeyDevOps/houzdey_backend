from bson import ObjectId
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException  # type: ignore
from typing import  List,  Optional
from fastapi.responses import JSONResponse
from pymongo import ASCENDING, DESCENDING
from app.core.database import property_collection
from app.api.deps import get_current_user
from app.models.property import Property, PropertyUpdate, PropertyResponse, SortOrder, SortBy
import json
from fastapi import status
from math import ceil
from datetime import datetime
from app.utils.cloudinary_config import upload_image_to_cloudinary, delete_image_from_cloudinary
from fastapi import status
from fastapi.responses import Response


router = APIRouter()




# GET A USER'S PROPERTIES
@router.get("/users/me/properties/")
async def get_user_properties(current_user=Depends(get_current_user)):
    user_id = str(current_user["id"])

    properties = []
    async for property in property_collection.find({"owner_id": user_id}):
        properties.append(property)

    if not properties:
        raise HTTPException(status_code=404, detail="No properties found for this user")
    return properties



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
    sort_by: SortBy = SortBy.CREATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=50)
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price cannot be greater than max_price")

    filter_query = {}


    
    if search:
        filter_query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"address": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"state": {"$regex": search, "$options": "i"}},
            {"lga": {"$regex": search, "$options": "i"}},

        ]
    
    # Apply filters
    if property_type:
        filter_query["type"] = property_type
    if bedrooms:
        filter_query["beds"] = bedrooms
    if bathrooms:
        filter_query["baths"] = bathrooms
    if location_state:
        filter_query["state"] = {"$regex": f"^{location_state}$", "$options": "i"}
    if location_area:
        filter_query["lga"] = {"$regex": f"^{location_area}$", "$options": "i"}
    if amenities:
        filter_query["amenities.name"] = {"$all": amenities}


    # Price range filter
    if min_price is not None or max_price is not None:
        filter_query["price"] = {}
        if min_price:
            filter_query["price"]["$gte"] = min_price
        if max_price:
            filter_query["price"]["$lte"] = max_price

    # Calculate pagination
    skip = (page - 1) * limit
    
    # Get total count for pagination
    total_count = await property_collection.count_documents(filter_query)
    total_pages = ceil(total_count / limit)

    # Apply sorting
    sort_direction = ASCENDING if sort_order.value == "asc" else DESCENDING
    cursor = property_collection.find(filter_query)\
        .sort(sort_by.value, sort_direction)\
        .skip(skip)\
        .limit(limit)
    
    properties = []
    async for property in cursor:
        property["id"] = str(property["_id"])
        del property["_id"]
        properties.append(property)
    
    return {
        "properties": properties,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }




# GET A PROPERTY BY ID 66eb45085bc5f324f674a07f
@router.get("/properties/{property_id}")
async def get_property_by_id(property_id: str):
    property_obj = await property_collection.find_one({"_id": ObjectId(property_id)})
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    return Property(**property_obj)


# DELETE A USER'S PROPERTY
@router.delete("/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_property(
    property_id: str, current_user=Depends(get_current_user)
):
    property_obj = await property_collection.find_one({"_id": ObjectId(property_id)})
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    if property_obj["owner_id"] != str(current_user["id"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this property"
        )

    delete_result = await property_collection.delete_one({"_id": ObjectId(property_id)})
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=400, detail="Property deletion failed")

    response_data = {
        "status": "success",
        "message": "Property deleted successfully",
    }
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=response_data)


# UPDATE A USER'S PROPERTY
@router.put("/properties/{property_id}", response_model=Property)
async def update_user_property(
    property_id: str,
    property_update: PropertyUpdate,
    current_user: dict = Depends(get_current_user),
):
    property_obj = await property_collection.find_one({"_id": ObjectId(property_id)})
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    if property_obj["owner_id"] != str(current_user["id"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to update this property"
        )

    update_data = property_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()

    update_result = await property_collection.update_one(
        {"_id": ObjectId(property_id)}, {"$set": update_data}
    )
    if update_result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Property update failed")

    updated_property = await property_collection.find_one(
        {"_id": ObjectId(property_id)}
    )
    return Property(**updated_property)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_property(
    title: str = Form(...),
    type: str = Form(...),
    price: float = Form(...),
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
    current_user=Depends(get_current_user)
):
    try:
        # Validate numeric fields
        beds = max(0, beds)  # Ensure non-negative
        baths = max(0, baths)
        toilets = max(0, toilets)

        
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
            
        # Create property document
        property_data = {
            "title": title,
            "type": type,
            "price": price,
            "description": description,
            "amenities": amenities_list,
            "images": image_urls,
            "location": f"{state}, {lga}, {ward}",
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
            "owner_id": str(current_user.id),  # Access id as attribute instead of dictionary key
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "view_count": 0,
            "status": "Available"
        }
        
        result = await property_collection.insert_one(property_data)
        property_data["id"] = str(result.inserted_id)
        del property_data["_id"]
        
        return property_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create property: {str(e)}"
        )


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: str,
    # current_user = Depends(get_current_user)
):
    try:
        # Find the property
        property = await property_collection.find_one({
            "_id": ObjectId(property_id)
        })

        if not property:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        # # Check if the current user owns the property
        # if str(property["owner_id"]) != str(current_user["id"]):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="You don't have permission to delete this property"
        #     )

        # Delete associated images from cloud storage
        if "images" in property:
            for image_url in property["images"]:
                try:
                    # Extract public_id from Cloudinary URL
                    public_id = image_url.split("/")[-1].split(".")[0]
                    await delete_image_from_cloudinary(public_id)
                except Exception as e:
                    print(f"Failed to delete image {image_url}: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to delete image from cloud storage"
                    )

        # Delete the property from database
        result = await property_collection.delete_one({
            "_id": ObjectId(property_id)
        })

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        print(f"Error deleting property: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete property"
        )
