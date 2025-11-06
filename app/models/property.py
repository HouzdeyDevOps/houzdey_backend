from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class SortBy(str, Enum):
    CREATED_AT = "created_at"
    PRICE = "price"

class ListingType(str, Enum):
    RENT = "rent"
    SALE = "sale"

class PropertyResponse(BaseModel):
    properties: List[dict]
    pagination: dict



class PropertyAmenity(BaseModel):
    name: str

class Property(BaseModel):
    id: Optional[str] = None
    title: str
    type: str
    price: float
    rental_price: Optional[float] = None
    sale_price: Optional[float] = None
    listing_type: ListingType = ListingType.RENT
    agency_fee: Optional[float] = None
    legal_fee: Optional[float] = None
    other_fees: Optional[float] = None
    amenities: List[PropertyAmenity]
    description: str
    images: List[str]
    video: Optional[str] = None
    location: str
    beds: int
    baths: int
    toilets: int
    condition: str
    furnishing: str
    address: str
    state: str
    lga: str  # Local Government Area
    ward: str
    estate: Optional[str]
    size: Optional[str] = None
    owner_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    view_count: int = 0
    status: str  # Available, Unavailable, pending, draft



class PropertyCreate(BaseModel):
    availability_status: str
    location_state: str
    location_area: str
    description: str
    price: float  # For backward compatibility
    rental_price: Optional[float] = None
    sale_price: Optional[float] = None
    listing_type: ListingType = ListingType.RENT
    property_address: str
    estate_name: str = None
    property_type: str
    condition: str
    furnishing: str
    bedrooms: int
    bathrooms: int
    toilets: int
    caution_fee: float | None = None
    agency_fee: float | None = None
    other_fees: float | None = None
    facilities: List[str] = []
    listing_by: str


class PropertyUpdate(BaseModel):
    availability_status: Optional[str]
    location_state: Optional[str]
    location_area: Optional[str]
    description: Optional[str]
    price: Optional[float]  # For backward compatibility
    rental_price: Optional[float]
    sale_price: Optional[float]
    listing_type: Optional[ListingType]
    property_address: Optional[str]
    estate_name: Optional[str]
    property_type: Optional[str]
    condition: Optional[str]
    furnishing: Optional[str]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    toilets: Optional[int]
    caution_fee: Optional[float]
    agency_fee: Optional[float]
    other_fees: Optional[float]
    facilities: Optional[List[str]]
    listing_by: Optional[str]