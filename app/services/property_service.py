from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from math import ceil
import json
import httpx

from app.services.base_service import BaseService
from app.repositories.property_repository import PropertyRepository
from app.repositories.user_repository import UserRepository
from app.repositories.review_repository import ReviewRepository
from app.models.property import SortBy, SortOrder, PropertyCreate, PropertyUpdate
from app.core.exceptions import ValidationError, NotFoundError, PermissionError, BusinessLogicError
from app.utils.slug import generate_property_slug


class PropertyService(BaseService):
    """Service for property-related business logic"""
    
    def __init__(self):
        self.property_repo = PropertyRepository()
        self.user_repo = UserRepository()
        self.review_repo = ReviewRepository()
    
    async def get_user_properties(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all properties owned by a user"""
        if not self.validate_object_id(user_id):
            raise ValidationError("Invalid user ID format")
        
        properties = await self.property_repo.find_by_owner_id(user_id)
        
        # Ensure all required fields are present
        for prop in properties:
            prop.setdefault("status", "available")
            prop.setdefault("created_at", datetime.utcnow().isoformat())
        
        return properties
    
    async def get_properties_with_filters(self,
                                        search: Optional[str] = None,
                                        min_price: Optional[float] = None,
                                        max_price: Optional[float] = None,
                                        property_type: Optional[str] = None,
                                        bedrooms: Optional[int] = None,
                                        bathrooms: Optional[int] = None,
                                        location_state: Optional[str] = None,
                                        location_area: Optional[str] = None,
                                        amenities: Optional[List[str]] = None,
                                        listing_type: Optional[str] = None,
                                        sort_by: SortBy = SortBy.CREATED_AT,
                                        sort_order: SortOrder = SortOrder.DESC,
                                        page: int = 1,
                                        limit: int = 12) -> Dict[str, Any]:
        """Get properties with advanced filtering and pagination"""
        
        # Validate pagination parameters
        if page < 1:
            raise ValidationError("Page must be greater than 0")
        if limit < 1 or limit > 50:
            raise ValidationError("Limit must be between 1 and 50")
        
        # Validate price range
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValidationError("min_price cannot be greater than max_price")
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get properties and total count
        properties, total_count = await self.property_repo.find_with_filters(
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
            skip=skip,
            limit=limit
        )
        
        # Calculate pagination info
        total_pages = ceil(total_count / limit)
        
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
    
    async def get_property_by_id(self, property_id: str) -> Dict[str, Any]:
        """Get a property by ID with owner and reviews information"""
        if not self.validate_object_id(property_id):
            raise ValidationError("Invalid property ID format")
        
        # Get the property
        property_obj = await self.property_repo.get_by_id(property_id)
        if not property_obj:
            raise NotFoundError("Property not found")
        
        # Get the owner information
        owner = await self.user_repo.get_by_id(property_obj["owner_id"])
        if owner:
            property_obj["host"] = {
                "id": owner["id"],
                "name": f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip(),
                "image": owner.get("profile_picture", ""),
                "company": owner.get("company", ""),
                "role": owner.get("bio", ""),
                "phone_number": owner.get("phone_number", "")
            }
        
        # Get reviews with user information
        reviews = await self.review_repo.find_by_property_id(property_id)
        enriched_reviews = []
        
        for review in reviews:
            review_user = await self.user_repo.get_by_id(review["user_id"])
            if review_user:
                enriched_reviews.append({
                    "id": review["id"],
                    "rating": review["rating"],
                    "comment": review["comment"],
                    "date": review["created_at"],
                    "user": {
                        "name": f"{review_user.get('first_name', '')} {review_user.get('last_name', '')}".strip(),
                        "image": review_user.get('profile_picture', '')
                    }
                })
        
        property_obj["reviews"] = enriched_reviews
        
        # Increment view count
        await self.property_repo.increment_view_count(property_id)
        
        return property_obj
    
    async def get_property_by_slug(self, slug: str) -> Dict[str, Any]:
        """Get a property by its SEO-friendly slug"""
        # Find property by slug
        property_obj = await self.property_repo.find_one({"slug": slug})
        self.ensure_exists(property_obj, "Property")
        
        # Get owner information
        owner = await self.user_repo.get_by_id(property_obj["owner_id"])
        if owner:
            property_obj["host"] = {
                "id": property_obj["owner_id"],
                "name": f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip(),
                "email": owner.get("email", ""),
                "phone_number": owner.get("phone_number", ""),
                "image": owner.get("profile_picture", ""),
                "company": owner.get("company", ""),
                "role": owner.get("role", "Property Owner")
            }   
        
        # Get reviews with user information
        reviews = await self.review_repo.find_by_property_id(property_obj["id"])
        enriched_reviews = []
        
        for review in reviews:
            review_user = await self.user_repo.get_by_id(review["user_id"])
            if review_user:
                enriched_reviews.append({
                    "id": review["id"],
                    "rating": review["rating"],
                    "comment": review["comment"],
                    "date": review["created_at"],
                    "user": {
                        "name": f"{review_user.get('first_name', '')} {review_user.get('last_name', '')}".strip(),
                        "image": review_user.get('profile_picture', '')
                    }
                })
        
        property_obj["reviews"] = enriched_reviews
        
        # Increment view count
        await self.property_repo.increment_view_count(property_obj["id"])
        
        return property_obj
    
    async def create_property(self, property_data: Dict[str, Any], owner_id: str) -> Dict[str, Any]:
        """Create a new property"""
        if not self.validate_object_id(owner_id):
            raise ValidationError("Invalid owner ID format")
        
        # Validate required fields
        required_fields = ["title", "type", "price", "description", "address", "state", "lga"]
        self.validate_required_fields(property_data, required_fields)
        
        # Validate numeric fields
        if "beds" in property_data:
            property_data["beds"] = max(0, property_data["beds"])
        if "baths" in property_data:
            property_data["baths"] = max(0, property_data["baths"])
        if "toilets" in property_data:
            property_data["toilets"] = max(0, property_data["toilets"])
        
        # Handle price logic for backward compatibility and new listing types
        listing_type = property_data.get("listing_type", "rent")
        price = property_data["price"]
        
        if listing_type == "rent":
            property_data["rental_price"] = property_data.get("rental_price", price)
            property_data["sale_price"] = property_data.get("sale_price")
        else:  # listing_type == "sale"
            property_data["rental_price"] = property_data.get("rental_price")
            property_data["sale_price"] = property_data.get("sale_price", price)
        
        # Set default values and metadata
        property_data.update({
            "owner_id": owner_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "view_count": 0,
            "status": "available",
            "listing_type": listing_type
        })
        
        # Build location field
        if "state" in property_data and "lga" in property_data and "ward" in property_data:
            property_data["location"] = f"{property_data['state']}, {property_data['lga']}, {property_data['ward']}"
        
        # Create the property first to get the ID
        created_property = await self.property_repo.create(property_data)
        
        # Generate SEO-friendly slug after getting the property ID
        if created_property and created_property.get("id"):
            slug = generate_property_slug(
                listing_type=property_data.get("listing_type", "rent"),
                beds=property_data.get("beds", 0),
                property_type=property_data.get("type", "property"),
                lga=property_data.get("lga", ""),
                state=property_data.get("state", ""),
                property_id=created_property["id"]
            )
            
            # Update property with slug
            await self.property_repo.update_by_id(created_property["id"], {"slug": slug})
            created_property["slug"] = slug
        
        return created_property
    
    async def update_property(self, property_id: str, property_update: Dict[str, Any], current_user_id: str) -> Dict[str, Any]:
        """Update a property"""
        if not self.validate_object_id(property_id):
            raise ValidationError("Invalid property ID format")
        
        # Get existing property
        property_obj = await self.property_repo.get_by_id(property_id)
        self.ensure_exists(property_obj, "Property")
        
        # Check ownership
        self.check_ownership(property_obj["owner_id"], current_user_id)
        
        # Sanitize update data
        update_data = self.sanitize_data(property_update)
        update_data["updated_at"] = datetime.utcnow()
        
        # Update the property
        success = await self.property_repo.update_by_id(property_id, update_data)
        if not success:
            raise BusinessLogicError("Property update failed")
        
        # Return updated property
        return await self.property_repo.get_by_id(property_id)
    
    async def delete_property(self, property_id: str, current_user_id: str) -> bool:
        """Delete a property"""
        if not self.validate_object_id(property_id):
            raise ValidationError("Invalid property ID format")
        
        # Get existing property
        property_obj = await self.property_repo.get_by_id(property_id)
        self.ensure_exists(property_obj, "Property")
        
        # Check ownership
        self.check_ownership(property_obj["owner_id"], current_user_id)
        
        # Delete associated images (this should be handled by a separate image service)
        # For now, we'll leave this as a comment for future implementation
        # await self.image_service.delete_property_images(property_obj.get("images", []))
        
        # Delete the property
        success = await self.property_repo.delete_by_id(property_id)
        if not success:
            raise BusinessLogicError("Property deletion failed")
        
        return True
    
    async def update_property_status(self, property_id: str, status: str, current_user_id: str) -> Dict[str, str]:
        """Update property status"""
        if not self.validate_object_id(property_id):
            raise ValidationError("Invalid property ID format")

        # Validate status
        valid_statuses = ["available", "unavailable", "draft", "pending approval"]
        if status.lower() not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

        # Get existing property
        property_obj = await self.property_repo.get_by_id(property_id)
        self.ensure_exists(property_obj, "Property")

        # Check ownership
        self.check_ownership(property_obj["owner_id"], current_user_id)

        # Update status
        success = await self.property_repo.update_status(property_id, status.lower())
        if not success:
            raise BusinessLogicError("Failed to update property status")

        return {"message": "Property status updated successfully"}

    async def import_property(self, import_data: Dict[str, Any], owner_id: str) -> Dict[str, Any]:
        """
        Import a property from an external source (e.g., n8n scraper).
        Handles image URLs and source tracking.
        """
        if not self.validate_object_id(owner_id):
            raise ValidationError("Invalid owner ID format")

        # Parse amenities from JSON string
        amenities_list = []
        if import_data.get("amenities"):
            try:
                amenities_list = json.loads(import_data["amenities"])
            except (json.JSONDecodeError, TypeError):
                amenities_list = []

        # Parse image URLs from JSON string
        image_urls = []
        if import_data.get("image_urls"):
            try:
                image_urls = json.loads(import_data["image_urls"])
            except (json.JSONDecodeError, TypeError):
                image_urls = []

        # Download and upload images to Cloudinary
        uploaded_images = await self._download_and_upload_images(image_urls)

        # Check for duplicate by source_id
        if import_data.get("source_id"):
            existing = await self.property_repo.find_one({
                "source_id": import_data["source_id"],
                "source": import_data.get("source", "external")
            })
            if existing:
                raise BusinessLogicError(f"Property already imported with source_id: {import_data['source_id']}")

        # Prepare property data
        property_data = {
            "title": import_data["title"],
            "type": import_data["type"],
            "price": import_data["price"],
            "description": import_data["description"],
            "beds": import_data.get("beds", 0),
            "baths": import_data.get("baths", 0),
            "toilets": import_data.get("toilets", 0),
            "condition": import_data.get("condition", "fairly-used"),
            "furnishing": import_data.get("furnishing", "unfurnished"),
            "address": import_data["address"],
            "state": import_data["state"],
            "lga": import_data["lga"],
            "ward": import_data.get("ward", ""),
            "estate": import_data.get("estate"),
            "size": import_data.get("size"),
            "listing_type": import_data.get("listing_type", "rent"),
            "amenities": amenities_list,
            "images": uploaded_images,
            "status": import_data.get("status", "pending approval"),
            "agency_fee": import_data.get("agency_fee"),
            "legal_fee": import_data.get("legal_fee"),
            "other_fees": import_data.get("other_fees"),
            # Agent details
            "agent_name": import_data.get("agent_name"),
            "agent_phone": import_data.get("agent_phone"),
            # Source tracking
            "source": import_data.get("source", "external"),
            "source_url": import_data.get("source_url"),
            "source_id": import_data.get("source_id"),
        }

        # Use the existing create_property method
        created_property = await self.create_property(property_data, owner_id)

        return {
            "success": True,
            "message": "Property imported successfully",
            "property_id": created_property.get("id"),
            "property_slug": created_property.get("slug"),
            "images_uploaded": len(uploaded_images)
        }

    async def _download_and_upload_images(self, image_urls: List[str], max_images: int = 10) -> List[str]:
        """Download images from URLs and upload to Cloudinary"""
        from app.utils.cloudinary_config import upload_image_to_cloudinary

        uploaded_urls = []

        # Limit number of images
        urls_to_process = image_urls[:max_images]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for url in urls_to_process:
                try:
                    # Download image
                    response = await client.get(url)
                    if response.status_code == 200:
                        # Upload to Cloudinary
                        cloudinary_url = await upload_image_to_cloudinary(
                            response.content,
                            "properties/imported"
                        )
                        if cloudinary_url:
                            uploaded_urls.append(cloudinary_url)
                except Exception as e:
                    # Log error but continue with other images
                    print(f"Failed to download/upload image {url}: {str(e)}")
                    continue

        return uploaded_urls