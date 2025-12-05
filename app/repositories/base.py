from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from app.core.database import PyObjectId

T = TypeVar('T')


class BaseRepository(ABC):
    """Abstract base repository class for common database operations"""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document"""
        result = await self.collection.insert_one(data)
        data["id"] = str(result.inserted_id)
        if "_id" in data:
            del data["_id"]
        return data
    
    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(id)})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
            return None
        except Exception:
            return None
    
    async def update_by_id(self, id: str, data: Dict[str, Any]) -> bool:
        """Update a document by ID"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(id)}, 
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    async def delete_by_id(self, id: str) -> bool:
        """Delete a document by ID"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception:
            return False
    
    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document matching the query"""
        try:
            doc = await self.collection.find_one(query)
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
            return None
        except Exception:
            return None
    
    async def find(self, query: Dict[str, Any] = None, 
                   skip: int = 0, 
                   limit: int = 0,
                   sort: List[tuple] = None) -> List[Dict[str, Any]]:
        """Find documents with optional pagination and sorting"""
        if query is None:
            query = {}
        
        cursor = self.collection.find(query)
        
        if sort:
            cursor = cursor.sort(sort)
        
        if skip > 0:
            cursor = cursor.skip(skip)
        
        if limit > 0:
            cursor = cursor.limit(limit)
        
        documents = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            documents.append(doc)
        
        return documents
    
    async def count(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching query"""
        if query is None:
            query = {}
        return await self.collection.count_documents(query)
    
    async def exists(self, query: Dict[str, Any]) -> bool:
        """Check if document exists"""
        count = await self.collection.count_documents(query, limit=1)
        return count > 0
    
    def _convert_object_ids(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ObjectId to string in document"""
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc