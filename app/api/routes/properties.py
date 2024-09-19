from bson import ObjectId
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException  # type: ignore
from typing import Annotated, List, Union
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING
from app.core.database import property_collection
from app.api.deps import get_current_user
from app.models.properties import Property, PropertyCreate, PropertyUpdate
from app.settings import settings
import cloudinary
import cloudinary.uploader
import json
from fastapi import status

from datetime import datetime


router = APIRouter()

# Setup Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)


@router.post(
    "/properties/",
    status_code=201,
)
async def create_property(
    property_data: str = Form(...),
    images: List[UploadFile] = File(...),
    current_user: str = Depends(get_current_user),
):
    # Parse property_data as JSON
    property_data_dict = json.loads(property_data)

    # Validate property data using Pydantic model
    property_create = PropertyCreate(**property_data_dict)

    # Upload images to Cloudinary
    image_urls = []
    for image in images:
        image_key = f"{current_user['id']}/{image.filename}"
        result = cloudinary.uploader.upload(image.file, public_id=image_key)
        # result = cloudinary.uploader.upload(image.file)
        # image_urls.append(result["secure_url"])

    # Prepare property data
    property_dict = property_create.dict()
    property_dict["images"] = image_urls
    property_dict["owner_id"] = str(current_user["id"])
    property_dict["created_at"] = datetime.utcnow()
    property_dict["updated_at"] = datetime.utcnow()
    property_dict["bookmarked_by_count"] = 0
    property_dict["view_count"] = 0

    # Insert into database
    result = await property_collection.insert_one(property_dict)

    # Add the id to the document
    await property_collection.update_one(
        {"_id": result.inserted_id}, {"$set": {"id": str(result.inserted_id)}}
    )

    response_data = {
        "status": "success",
        "message": "Property created successfully",
    }

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response_data)


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


# # GET ALL PROPERTIES , response_model=List[Property]
# @router.get("/properties/")
# async def get_all_properties():
#     # .to_list(1000)
#     properties = []
#     try:
#         async for property in property_collection.find():
#             property["_id"] = str(property["_id"])  # Convert ObjectId to string
#             properties.append(property)
#         return properties
#     except Exception as e:
#         print(e)
#         return []


@router.get("/properties")
async def get_all_properties(
    location_state: Annotated[
        str | None, Query(description="State where the property is located")
    ] = None,
    location_area: Annotated[
        str | None, Query(description="Area where the property is located")
    ] = None,
    min_price: Annotated[Union[float, str, None], Query(description="Minimum price", gt=0)] = None,
    max_price: Annotated[Union[float, str, None], Query(description="Maximum price", gt=0)] = None,
    # min_price: Annotated[float | None, Query(description="Minimum price", gt=0)] = None,
    # max_price: Annotated[float | None, Query(description="Maximum price", gt=0)] = None,
    property_type: Annotated[str | None, Query(...)] = None,
    bedrooms: Annotated[int | None, Query(...)] = None,
    bathrooms: Annotated[int | None, Query(...)] = None,
    furnishing: Annotated[str | None, Query(...)] = None,
    condition: Annotated[str | None, Query(...)] = None,
    facilities: Annotated[List[str] | None, Query(...)] = None,
    sort_by: Annotated[str | None, Query(...)] = "price",
    sort_order: Annotated[str | None, Query(...)] = "asc",
):
    min_price = int(min_price) 
    max_price = int(max_price)

    filter_query = {}
    if location_state and location_state != "" and location_state != "null":
        filter_query["location_state"] = location_state
    if location_area and location_area != "" and location_area != "null":
        filter_query["location_area"] = location_area
    if property_type and property_type != "" and property_type != "null":
        filter_query["property_type"] = property_type
    if bedrooms and bedrooms != "" and bedrooms != "null":
        filter_query["bedrooms"] = bedrooms
    if bathrooms and bathrooms != "" and bathrooms != "null":
        filter_query["bathrooms"] = bathrooms
    if furnishing and furnishing != "" and furnishing != "null":
        filter_query["furnishing"] = furnishing
    if condition and condition != "" and condition != "null":
        filter_query["condition"] = condition
    if facilities and facilities != "" and facilities != "null":
        filter_query["facilities"] = {"$all": facilities}

    

    if min_price is not None or max_price is not None:
        price_query = {}
    # if price state and if not an empty
        if min_price is not None and min_price < max_price and max_price != "":
            price_query["$gte"] = min_price
        if max_price is not None and max_price != "" and max_price > min_price:
            price_query["$lte"] = max_price
        filter_query["price"] = price_query

    sort_direction = ASCENDING if sort_order.lower() == "asc" else DESCENDING
    sort_options = [(sort_by, sort_direction)]

    properties = []
    try:
        cursor = property_collection.find(filter_query).sort(sort_options)
        async for property in cursor:
            property["_id"] = str(property["_id"])  # Convert ObjectId to string
            properties.append(property)
        return properties
    except Exception as e:
        print(e)
        return []


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
