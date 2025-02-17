from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional






class Property(BaseModel):
    id: str = Field(..., description="Property ID")
    title: str
    type: str  # Matches PropertyType enum from frontend
    price: float
    amenities: List[dict]  # Contains {name: string, icon: string}
    description: str
    images: List[str]
    location: str
    beds: int
    baths: int
    address: str
    state: str
    lga: str  # Local Government Area
    ward: str
    estate: Optional[str]
    size: str
    owner_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    view_count: int = 0
    bookmarked_by_count: int = 0

    property_address: str = Field(..., description="Property Address")
    estate_name: str = Field(default=None, description="Estate Name")
    property_type: str = Field(..., description="Property Type", max_length=50)
    condition: str = Field(..., description="Condition of the property")
    furnishing: str = Field(..., description="Furnishing state")
    bedrooms: int = Field(..., description="Number of bedrooms")
    bathrooms: int = Field(..., description="Number of bathrooms")
    toilets: int = Field(..., description="Number of toilets")
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