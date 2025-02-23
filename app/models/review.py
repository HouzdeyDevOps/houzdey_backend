from pydantic import BaseModel
from datetime import datetime

class ReviewCreate(BaseModel):
    property_id: str
    rating: float
    comment: str

class Review(ReviewCreate):
    id: str
    user_id: str
    created_at: datetime 