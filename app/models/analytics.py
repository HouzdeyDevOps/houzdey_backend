from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class AnalyticsTimeframe(str, Enum):
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"

class PropertyView(BaseModel):
    """Model for tracking property views"""
    id: Optional[str] = None
    property_id: str
    user_id: Optional[str] = None  # None for anonymous users
    ip_address: str
    user_agent: str
    referrer: Optional[str] = None
    session_id: str
    viewed_at: datetime = Field(default_factory=datetime.utcnow)
    view_duration: Optional[int] = None  # in seconds

class PropertyInquiry(BaseModel):
    """Model for tracking property inquiries"""
    id: Optional[str] = None
    property_id: str
    user_id: str
    inquiry_type: str  # "chat", "phone", "email", "viewing_request"
    message: Optional[str] = None
    phone_number: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # "pending", "responded", "converted", "closed"

class PropertyAnalytics(BaseModel):
    """Comprehensive property analytics model"""
    property_id: str
    property_title: str
    property_type: str
    listing_type: str
    price: float
    
    # View metrics
    total_views: int
    unique_views: int
    views_today: int
    views_this_week: int
    views_this_month: int
    
    # Engagement metrics
    total_inquiries: int
    inquiries_today: int
    inquiries_this_week: int
    inquiries_this_month: int
    conversion_rate: float  # inquiries / unique_views
    
    # Time metrics
    average_view_duration: float
    bounce_rate: float  # single page views / total views
    
    # Geographic data
    top_locations: List[Dict[str, Any]]
    
    # Time series data
    daily_views: List[Dict[str, Any]]
    daily_inquiries: List[Dict[str, Any]]
    
    # Comparison metrics
    similar_properties_avg_views: float
    performance_rank: int  # rank among similar properties
    
    # Recommendations
    recommendations: List[str]
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class OwnerDashboardStats(BaseModel):
    """Dashboard statistics for property owners"""
    owner_id: str
    total_properties: int
    active_properties: int
    total_views: int
    total_inquiries: int
    total_messages: int
    
    # Performance metrics
    best_performing_property: Optional[Dict[str, Any]]
    average_views_per_property: float
    average_inquiries_per_property: float
    
    # Recent activity
    recent_views: List[Dict[str, Any]]
    recent_inquiries: List[Dict[str, Any]]
    
    # Trends
    views_trend: float  # percentage change from previous period
    inquiries_trend: float
    
    # Revenue insights (for paid features)
    estimated_monthly_revenue: float
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MarketInsights(BaseModel):
    """Market insights for property owners"""
    location: str
    property_type: str
    listing_type: str
    
    # Market data
    average_price: float
    price_trend: float  # percentage change
    total_listings: int
    active_listings: int
    
    # Demand metrics
    average_views_per_listing: float
    average_inquiries_per_listing: float
    average_time_on_market: int  # in days
    
    # Competition analysis
    similar_properties_count: int
    price_position: str  # "below_market", "market_rate", "above_market"
    
    # Recommendations
    suggested_price_range: Dict[str, float]
    market_recommendations: List[str]
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PropertyPerformanceMetrics(BaseModel):
    """Detailed performance metrics for a property"""
    property_id: str
    timeframe: AnalyticsTimeframe
    
    # Core metrics
    views: int
    unique_visitors: int
    inquiries: int
    messages: int
    phone_calls: int
    
    # Engagement quality
    avg_session_duration: float
    pages_per_session: float
    bounce_rate: float
    
    # Conversion funnel
    view_to_inquiry_rate: float
    inquiry_to_message_rate: float
    
    # Traffic sources
    traffic_sources: Dict[str, int]
    
    # User demographics
    visitor_locations: Dict[str, int]
    device_types: Dict[str, int]
    
    # Time patterns
    peak_viewing_hours: List[int]
    peak_viewing_days: List[str]
    
    period_start: datetime
    period_end: datetime
    generated_at: datetime = Field(default_factory=datetime.utcnow) 