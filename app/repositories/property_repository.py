from typing import Dict, List, Optional, Any
from pymongo import ASCENDING, DESCENDING
from app.repositories.base import BaseRepository
from app.core.database import property_collection
from app.models.property import SortBy, SortOrder


class PropertyRepository(BaseRepository):
    """Repository for property data access operations"""
    
    def __init__(self):
        super().__init__(property_collection)
    
    async def find_by_owner_id(self, owner_id: str) -> List[Dict[str, Any]]:
        """Find all properties by owner ID"""
        return await self.find({"owner_id": owner_id})
    
    async def find_with_filters(self, 
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
                               skip: int = 0,
                               limit: int = 12) -> tuple[List[Dict[str, Any]], int]:
        """Find properties with advanced filtering and return results with total count"""
        
        # Build filter query
        filter_query = {"status": "available"}
        
        # Search functionality
        if search:
            filter_query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"address": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"state": {"$regex": search, "$options": "i"}},
                {"lga": {"$regex": search, "$options": "i"}},
            ]
        
        # Property type filter
        if property_type:
            filter_query["type"] = property_type
        
        # Bedroom and bathroom filters
        if bedrooms:
            filter_query["beds"] = bedrooms
        if bathrooms:
            filter_query["baths"] = bathrooms
        
        # Location filters
        if location_state:
            filter_query["state"] = {"$regex": f"^{location_state}$", "$options": "i"}
        if location_area:
            filter_query["lga"] = {"$regex": f"^{location_area}$", "$options": "i"}
        
        # Amenities filter
        if amenities:
            filter_query["amenities.name"] = {"$all": amenities}
        
        # Listing type filter
        if listing_type:
            filter_query["listing_type"] = listing_type
        
        # Price range filter
        if min_price is not None or max_price is not None:
            if not listing_type:
                # For backward compatibility, search in the price field
                filter_query["price"] = {}
                if min_price:
                    filter_query["price"]["$gte"] = min_price
                if max_price:
                    filter_query["price"]["$lte"] = max_price
            else:
                # Search in the appropriate price field based on listing type
                price_field = "rental_price" if listing_type == "rent" else "sale_price"
                filter_query[price_field] = {}
                if min_price:
                    filter_query[price_field]["$gte"] = min_price
                if max_price:
                    filter_query[price_field]["$lte"] = max_price
        
        # Get total count
        total_count = await self.count(filter_query)
        
        # Apply sorting
        sort_direction = ASCENDING if sort_order.value == "asc" else DESCENDING
        sort_list = [(sort_by.value, sort_direction)]
        
        # Get properties
        properties = await self.find(filter_query, skip=skip, limit=limit, sort=sort_list)
        
        return properties, total_count
    
    async def find_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Find properties by status"""
        return await self.find({"status": status})
    
    async def update_status(self, property_id: str, status: str) -> bool:
        """Update property status"""
        return await self.update_by_id(property_id, {"status": status})
    
    async def increment_view_count(self, property_id: str) -> bool:
        """Increment property view count"""
        try:
            result = await self.collection.update_one(
                {"_id": self._to_object_id(property_id)},
                {"$inc": {"view_count": 1}}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    def _to_object_id(self, id_str: str):
        """Convert string ID to ObjectId"""
        from bson import ObjectId
        return ObjectId(id_str)