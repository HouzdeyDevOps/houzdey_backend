"""Dependency injection for services and repositories"""

from functools import lru_cache
from typing import Annotated
from fastapi import Depends

# Repository imports
from app.repositories.user_repository import UserRepository
from app.repositories.property_repository import PropertyRepository
from app.repositories.review_repository import ReviewRepository, ReviewSummaryRepository

# Service imports
from app.services.user_service import UserService
from app.services.property_service import PropertyService
from app.services.review_service import ReviewService
from app.services.notification_service import NotificationService


# Repository Dependencies
@lru_cache()
def get_user_repository() -> UserRepository:
    """Get user repository instance"""
    return UserRepository()


@lru_cache()
def get_property_repository() -> PropertyRepository:
    """Get property repository instance"""
    return PropertyRepository()


@lru_cache()
def get_review_repository() -> ReviewRepository:
    """Get review repository instance"""
    return ReviewRepository()


@lru_cache()
def get_review_summary_repository() -> ReviewSummaryRepository:
    """Get review summary repository instance"""
    return ReviewSummaryRepository()


# Service Dependencies
@lru_cache()
def get_user_service() -> UserService:
    """Get user service instance"""
    return UserService()


@lru_cache()
def get_property_service() -> PropertyService:
    """Get property service instance"""
    return PropertyService()


@lru_cache()
def get_review_service() -> ReviewService:
    """Get review service instance"""
    return ReviewService()


@lru_cache()
def get_notification_service() -> NotificationService:
    """Get notification service instance"""
    return NotificationService()


# Type aliases for dependency injection
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
PropertyRepositoryDep = Annotated[PropertyRepository, Depends(get_property_repository)]
ReviewRepositoryDep = Annotated[ReviewRepository, Depends(get_review_repository)]
ReviewSummaryRepositoryDep = Annotated[ReviewSummaryRepository, Depends(get_review_summary_repository)]

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
PropertyServiceDep = Annotated[PropertyService, Depends(get_property_service)]
ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]
NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]