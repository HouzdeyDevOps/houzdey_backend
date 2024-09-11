from fastapi import APIRouter, HTTPException, Depends
from app.models import ReviewResponse
from app.models import User, ReviewCreate, ReviewResponse
from app.dependencies import get_current_user
from app.crud import create_review, get_reviews_for_property
from typing import List


router = APIRouter(prefix="/api/v1", tags=["reviews"])


@router.post("/review/{property_id}")
async def review_property(property_id: str, review_data: ReviewCreate, current_user: User = Depends(get_current_user)):

    review_data.property_id = property_id
    review_id = await create_review(review_data)
    return {"message": "Review created successfully", "review_id": review_id}


@router.get("/review/{property_id}", response_model=List[ReviewResponse])
async def get_reviews_for_property_route(property_id: str):
    reviews = await get_reviews_for_property(property_id)
    if not reviews:
        raise HTTPException(
            status_code=404, detail="No reviews found for this property")
    return reviews
