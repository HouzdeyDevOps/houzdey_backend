from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from bson import ObjectId

class ReviewSentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class ReviewCategory(str, Enum):
    COMMUNICATION = "communication"
    PROFESSIONALISM = "professionalism"
    RELIABILITY = "reliability"
    KNOWLEDGE = "knowledge"
    RESPONSIVENESS = "responsiveness"
    OVERALL = "overall"

class ReviewStatus(str, Enum):
    ACTIVE = "active"
    HIDDEN = "hidden"
    FLAGGED = "flagged"
    DELETED = "deleted"

class ReviewReply(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str  # User who wrote the reply
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_edited: bool = False
    likes_count: int = 0
    liked_by: List[str] = []  # User IDs who liked this reply

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class Review(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    reviewer_id: str  # User who wrote the review
    reviewed_user_id: str  # User being reviewed
    
    # Review content
    rating: int = Field(..., ge=1, le=5)  # 1-5 star rating
    title: Optional[str] = None
    content: str
    sentiment: ReviewSentiment
    categories: List[ReviewCategory] = []  # What aspects are being reviewed
    
    # Context
    interaction_type: Optional[str] = None  # "property_inquiry", "rental", "purchase", etc.
    property_id: Optional[str] = None  # Related property if applicable
    transaction_id: Optional[str] = None  # Related transaction if applicable
    
    # Status and moderation
    status: ReviewStatus = ReviewStatus.ACTIVE
    is_verified: bool = False  # If the interaction was verified
    is_anonymous: bool = False
    
    # Engagement
    likes_count: int = 0
    liked_by: List[str] = []  # User IDs who liked this review
    replies: List[ReviewReply] = []
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_edited: bool = False
    
    # Moderation
    flagged_by: List[str] = []  # User IDs who flagged this review
    flag_reasons: List[str] = []
    moderated_at: Optional[datetime] = None
    moderated_by: Optional[str] = None  # Admin user ID
    moderation_notes: Optional[str] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class ReviewSummary(BaseModel):
    user_id: str
    total_reviews: int = 0
    average_rating: float = 0.0
    
    # Sentiment breakdown
    positive_count: int = 0
    neutral_count: int = 0
    negative_count: int = 0
    
    # Rating distribution
    five_star_count: int = 0
    four_star_count: int = 0
    three_star_count: int = 0
    two_star_count: int = 0
    one_star_count: int = 0
    
    # Category ratings
    communication_rating: float = 0.0
    professionalism_rating: float = 0.0
    reliability_rating: float = 0.0
    knowledge_rating: float = 0.0
    responsiveness_rating: float = 0.0
    
    # Recent activity
    recent_reviews: List[Review] = []
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class ReviewFilters(BaseModel):
    sentiment: Optional[ReviewSentiment] = None
    rating: Optional[int] = None
    category: Optional[ReviewCategory] = None
    interaction_type: Optional[str] = None
    is_verified: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class CreateReviewRequest(BaseModel):
    reviewed_user_id: str
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = None
    content: str
    categories: List[ReviewCategory] = []
    interaction_type: Optional[str] = None
    property_id: Optional[str] = None
    is_anonymous: bool = False

class UpdateReviewRequest(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = None
    content: Optional[str] = None
    categories: Optional[List[ReviewCategory]] = None

class CreateReplyRequest(BaseModel):
    content: str

class ReviewReportRequest(BaseModel):
    reason: str
    description: Optional[str] = None 