from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from bson.errors import InvalidId
import logging
from collections import defaultdict

from app.core.database import (
    property_collection,
    property_views_collection,
    property_inquiries_collection,
    conversation_collection,
    message_collection,
    user_collection,
    analytics_cache_collection
)
from app.api.deps import get_current_user
from app.models.user import User
from app.models.analytics import (
    PropertyView,
    PropertyInquiry,
    PropertyAnalytics,
    OwnerDashboardStats,
    MarketInsights,
    PropertyPerformanceMetrics,
    AnalyticsTimeframe
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Helper function to track property views
async def track_property_view(property_id: str, request: Request, user_id: Optional[str] = None):
    """Track a property view"""
    try:
        # Get client IP and user agent
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        referrer = request.headers.get("referer")
        
        # Generate session ID (in real app, use proper session management)
        session_id = f"{ip_address}_{user_agent}"[:50]
        
        view = PropertyView(
            property_id=property_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            session_id=session_id
        )
        
        await property_views_collection.insert_one(view.model_dump())
        
        # Update property view count
        await property_collection.update_one(
            {"_id": ObjectId(property_id)},
            {"$inc": {"view_count": 1}}
        )
        
    except Exception as e:
        logger.error(f"Error tracking property view: {str(e)}")

@router.post("/track-view/{property_id}")
async def track_view(
    property_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Track a property view"""
    try:
        # Get client IP and user agent
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        session_id = f"{ip_address}_{user_agent}"[:50]
        
        view = PropertyView(
            property_id=property_id,
            user_id=str(current_user.id),
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        
        await property_views_collection.insert_one(view.model_dump())
        
        # Update property view count
        await property_collection.update_one(
            {"_id": ObjectId(property_id)},
            {"$inc": {"view_count": 1}}
        )
        
        return {"status": "tracked"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/owner/dashboard")
async def get_owner_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get dashboard statistics for property owners"""
    try:
        owner_id = str(current_user.id)
        
        # Get owner's properties
        total_properties = await property_collection.count_documents({"owner_id": owner_id})
        active_properties = await property_collection.count_documents({
            "owner_id": owner_id,
            "status": "available"
        })
        
        # Get property IDs for analytics
        property_ids = []
        async for prop in property_collection.find({"owner_id": owner_id}):
            property_ids.append(str(prop["_id"]))
        
        # Get view statistics
        total_views = await property_views_collection.count_documents({
            "property_id": {"$in": property_ids}
        }) if property_ids else 0
        
        # Mock data for other statistics
        return OwnerDashboardStats(
            owner_id=owner_id,
            total_properties=total_properties,
            active_properties=active_properties,
            total_views=total_views,
            total_inquiries=0,  # Will be implemented with inquiry tracking
            total_messages=0,   # Will be implemented with message tracking
            best_performing_property=None,
            average_views_per_property=total_views / total_properties if total_properties > 0 else 0,
            average_inquiries_per_property=0,
            recent_views=[],
            recent_inquiries=[],
            views_trend=0,
            inquiries_trend=0,
            estimated_monthly_revenue=0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard statistics: {str(e)}")

@router.get("/property/{property_id}")
async def get_property_analytics(
    property_id: str,
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.MONTH,
    current_user: User = Depends(get_current_user)
):
    """Get detailed analytics for a specific property"""
    try:
        # Verify property ownership
        property_obj = await property_collection.find_one({"_id": ObjectId(property_id)})
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")
        
        if property_obj["owner_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to view this property's analytics")
        
        # Calculate date range based on timeframe
        end_date = datetime.utcnow()
        if timeframe == AnalyticsTimeframe.WEEK:
            start_date = end_date - timedelta(days=7)
        elif timeframe == AnalyticsTimeframe.MONTH:
            start_date = end_date - timedelta(days=30)
        elif timeframe == AnalyticsTimeframe.QUARTER:
            start_date = end_date - timedelta(days=90)
        else:  # YEAR
            start_date = end_date - timedelta(days=365)
        
        # Get view metrics
        total_views = await property_views_collection.count_documents({
            "property_id": property_id
        })
        
        unique_views = await property_views_collection.count_documents({
            "property_id": property_id,
            "user_id": {"$ne": None}
        })
        
        views_in_period = await property_views_collection.count_documents({
            "property_id": property_id,
            "viewed_at": {"$gte": start_date, "$lte": end_date}
        })
        
        # Get today's views
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        views_today = await property_views_collection.count_documents({
            "property_id": property_id,
            "viewed_at": {"$gte": today_start}
        })
        
        # Get week views
        week_start = end_date - timedelta(days=7)
        views_this_week = await property_views_collection.count_documents({
            "property_id": property_id,
            "viewed_at": {"$gte": week_start}
        })
        
        # Get month views
        month_start = end_date - timedelta(days=30)
        views_this_month = await property_views_collection.count_documents({
            "property_id": property_id,
            "viewed_at": {"$gte": month_start}
        })
        
        # Get inquiry metrics
        total_inquiries = await property_inquiries_collection.count_documents({
            "property_id": property_id
        })
        
        inquiries_today = await property_inquiries_collection.count_documents({
            "property_id": property_id,
            "created_at": {"$gte": today_start}
        })
        
        inquiries_this_week = await property_inquiries_collection.count_documents({
            "property_id": property_id,
            "created_at": {"$gte": week_start}
        })
        
        inquiries_this_month = await property_inquiries_collection.count_documents({
            "property_id": property_id,
            "created_at": {"$gte": month_start}
        })
        
        # Calculate conversion rate
        conversion_rate = (total_inquiries / unique_views * 100) if unique_views > 0 else 0
        
        # Get daily view data for chart
        daily_views = []
        for i in range(30):  # Last 30 days
            day = end_date - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            views = await property_views_collection.count_documents({
                "property_id": property_id,
                "viewed_at": {"$gte": day_start, "$lt": day_end}
            })
            
            daily_views.insert(0, {
                "date": day_start.strftime("%Y-%m-%d"),
                "views": views
            })
        
        # Get daily inquiry data
        daily_inquiries = []
        for i in range(30):  # Last 30 days
            day = end_date - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            inquiries = await property_inquiries_collection.count_documents({
                "property_id": property_id,
                "created_at": {"$gte": day_start, "$lt": day_end}
            })
            
            daily_inquiries.insert(0, {
                "date": day_start.strftime("%Y-%m-%d"),
                "inquiries": inquiries
            })
        
        # Mock data for additional metrics
        average_view_duration = 2.5  # minutes
        bounce_rate = 65.5  # percentage
        top_locations = [
            {"location": "Lagos", "views": 45},
            {"location": "Abuja", "views": 23},
            {"location": "Port Harcourt", "views": 12}
        ]
        
        # Get similar properties average (mock calculation)
        similar_properties_avg_views = 25.5
        performance_rank = 3
        
        recommendations = [
            "Consider updating your property photos for better engagement",
            "Your response time to inquiries could be improved",
            "Add more detailed property description"
        ]
        
        return PropertyAnalytics(
            property_id=property_id,
            property_title=property_obj.get("title", "Unknown"),
            property_type=property_obj.get("type", "Unknown"),
            listing_type=property_obj.get("listing_type", "rent"),
            price=property_obj.get("price", 0),
            total_views=total_views,
            unique_views=unique_views,
            views_today=views_today,
            views_this_week=views_this_week,
            views_this_month=views_this_month,
            total_inquiries=total_inquiries,
            inquiries_today=inquiries_today,
            inquiries_this_week=inquiries_this_week,
            inquiries_this_month=inquiries_this_month,
            conversion_rate=conversion_rate,
            average_view_duration=average_view_duration,
            bounce_rate=bounce_rate,
            top_locations=top_locations,
            daily_views=daily_views,
            daily_inquiries=daily_inquiries,
            similar_properties_avg_views=similar_properties_avg_views,
            performance_rank=performance_rank,
            recommendations=recommendations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting property analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get property analytics")

@router.get("/market-insights")
async def get_market_insights(
    state: str = Query(..., description="State name"),
    property_type: str = Query(..., description="Property type"),
    listing_type: str = Query(default="rent", description="Listing type (rent/sale)"),
    current_user: User = Depends(get_current_user)
):
    """Get market insights for a specific location and property type"""
    try:
        # Get properties in the same market
        market_filter = {
            "state": {"$regex": f"^{state}$", "$options": "i"},
            "type": property_type,
            "listing_type": listing_type,
            "status": "available"
        }
        
        market_properties = []
        async for prop in property_collection.find(market_filter):
            market_properties.append(prop)
        
        if not market_properties:
            # Return empty insights if no properties found
            return MarketInsights(
                location=state,
                property_type=property_type,
                listing_type=listing_type,
                average_price=0,
                price_trend=0,
                total_listings=0,
                active_listings=0,
                average_views_per_listing=0,
                average_inquiries_per_listing=0,
                average_time_on_market=0,
                similar_properties_count=0,
                price_position="market_rate",
                suggested_price_range={"min": 0, "max": 0},
                market_recommendations=["No data available for this market"]
            )
        
        # Calculate market statistics
        prices = [prop.get("price", 0) for prop in market_properties]
        average_price = sum(prices) / len(prices) if prices else 0
        
        total_listings = len(market_properties)
        active_listings = len([p for p in market_properties if p.get("status") == "available"])
        
        # Calculate view and inquiry averages
        property_ids = [str(prop["_id"]) for prop in market_properties]
        
        total_market_views = await property_views_collection.count_documents({
            "property_id": {"$in": property_ids}
        })
        
        total_market_inquiries = await property_inquiries_collection.count_documents({
            "property_id": {"$in": property_ids}
        })
        
        avg_views_per_listing = total_market_views / total_listings if total_listings > 0 else 0
        avg_inquiries_per_listing = total_market_inquiries / total_listings if total_listings > 0 else 0
        
        # Mock data for additional metrics
        price_trend = 5.2  # percentage increase
        avg_time_on_market = 45  # days
        
        # Price recommendations
        sorted_prices = sorted(prices)
        price_25th = sorted_prices[len(sorted_prices) // 4] if sorted_prices else 0
        price_75th = sorted_prices[3 * len(sorted_prices) // 4] if sorted_prices else 0
        
        suggested_price_range = {
            "min": price_25th,
            "max": price_75th
        }
        
        market_recommendations = [
            f"Average price in {state} for {property_type} is ₦{average_price:,.0f}",
            f"Properties typically receive {avg_views_per_listing:.0f} views per month",
            f"Market has grown by {price_trend:.1f}% in the last quarter"
        ]
        
        return MarketInsights(
            location=state,
            property_type=property_type,
            listing_type=listing_type,
            average_price=average_price,
            price_trend=price_trend,
            total_listings=total_listings,
            active_listings=active_listings,
            average_views_per_listing=avg_views_per_listing,
            average_inquiries_per_listing=avg_inquiries_per_listing,
            average_time_on_market=avg_time_on_market,
            similar_properties_count=len(market_properties),
            price_position="market_rate",
            suggested_price_range=suggested_price_range,
            market_recommendations=market_recommendations
        )
        
    except Exception as e:
        logger.error(f"Error getting market insights: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get market insights")

@router.post("/inquiry")
async def track_property_inquiry(
    property_id: str,
    inquiry_type: str,
    message: Optional[str] = None,
    phone_number: Optional[str] = None,
    preferred_contact_method: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Track a property inquiry"""
    try:
        inquiry = PropertyInquiry(
            property_id=property_id,
            user_id=str(current_user.id),
            inquiry_type=inquiry_type,
            message=message,
            phone_number=phone_number,
            preferred_contact_method=preferred_contact_method
        )
        
        result = await property_inquiries_collection.insert_one(inquiry.model_dump())
        
        # TODO: Send notification to property owner
        # await notification_service.send_notification(...)
        
        return {"status": "tracked", "inquiry_id": str(result.inserted_id)}
        
    except Exception as e:
        logger.error(f"Error tracking property inquiry: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to track inquiry") 