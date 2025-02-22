from typing import List
from pydantic import BaseModel

class WishlistItem(BaseModel):
    user_id: str
    property_id: str

class WishlistResponse(BaseModel):
    items: List[str] 