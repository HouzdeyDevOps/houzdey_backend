from abc import ABC
from typing import Dict, Any, Optional
import logging
from app.core.exceptions import ValidationError, NotFoundError, PermissionError


class BaseService(ABC):
    """Base service class with common functionality"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_object_id(self, id_str: str) -> bool:
        """Validate if string is a valid ObjectId format"""
        try:
            from bson import ObjectId
            ObjectId(id_str)
            return True
        except Exception:
            return False
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: list) -> None:
        """Validate that all required fields are present"""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    def sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove None values and empty strings from data"""
        return {k: v for k, v in data.items() if v is not None and v != ""}
    
    def check_ownership(self, resource_owner_id: str, current_user_id: str) -> None:
        """Check if current user owns the resource"""
        if str(resource_owner_id) != str(current_user_id):
            raise PermissionError("You don't have permission to access this resource")
    
    def ensure_exists(self, resource: Optional[Dict[str, Any]], resource_name: str = "Resource") -> Dict[str, Any]:
        """Ensure resource exists, raise NotFoundError if not"""
        if not resource:
            raise NotFoundError(f"{resource_name} not found")
        return resource