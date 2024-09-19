from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional






class Property(BaseModel):
    id: str = Field(..., description="Property ID")
    availability_status: str = Field(..., description="Availability status (e.g., Available, Rented)")
    location_state: str = Field(..., description="Location state")
    location_area: str = Field(..., description="Location area")
    images: List[str] = Field(..., description="List of image URLs")
    description: str = Field(..., description="Description of the property", max_length=500)
    price: float = Field(..., description="Price per annum", gt=0,)
    owner_id: str = Field(..., description="Owner ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    property_address: str = Field(..., description="Property Address")
    estate_name: str = Field(default=None, description="Estate Name")
    property_type: str = Field(..., description="Property Type", max_length=50)
    condition: str = Field(..., description="Condition of the property")
    furnishing: str = Field(..., description="Furnishing state")
    bedrooms: int = Field(..., description="Number of bedrooms")
    bathrooms: int = Field(..., description="Number of bathrooms")
    toilets: int = Field(..., description="Number of toilets")
    bookmarked_by_count: int = 0  # Number of people who bookmarked/saved the property
    view_count: int = 0 # Number of views


    caution_fee: float = Field(None, description="Caution fee")
    agency_fee: float = Field(None, description="Agency fee")
    other_fees: float = Field(None, description="Other fees")


    facilities: List[str] = Field(None, description="List of facilities (e.g., Running Water, Power Supply)")
    listing_by: str = Field(..., description="Listed by (owner/agent)")
    


class PropertyCreate(BaseModel):
    availability_status: str
    location_state: str
    location_area: str
    description: str
    price: float
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
    price: Optional[float]
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