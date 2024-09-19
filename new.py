from datetime import datetime
from pydantic import BaseModel, Field, conint, constr, condecimal
from typing import Optional, List



class Property(BaseModel):
    id: str = Field(..., alias="_id")
    availability_status: str
    location_state: str
    location_area: str
    images: List[str] = Field(..., description="List of image URLs")
    description: constr(max_length=850) = Field(..., description="Description of the property")
    price: condecimal = Field(..., description="Price per annum", gt=0, max_digits=12, decimal_places=2)
    owner_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


    property_address: constr(max_length=60) = Field(..., description="Property Address")
    estate_name: Optional[constr(max_length=60)] = Field(None, description="Estate Name")
    property_type: constr(max_length=50) = Field(..., description="Property Type")
    condition: constr(max_length=50) = Field(..., description="Condition of the property")
    furnishing: constr(max_length=50) = Field(..., description="Furnishing state")
    bedrooms: conint(gt=0) = Field(..., description="Number of bedrooms")
    bathrooms: conint(gt=0) = Field(..., description="Number of bathrooms")
    toilets: conint(gt=0) = Field(..., description="Number of toilets")
    bookmarked_by_count: int = 0  # Number of people who bookmarked/saved the property
    view_count: int = 0


    caution_fee: Optional[condecimal(max_digits=10, decimal_places=2)] = Field(None, description="Caution fee")
    agency_fee: Optional[condecimal(max_digits=10, decimal_places=2)] = Field(None, description="Agency fee")
    other_fees: Optional[condecimal(max_digits=10, decimal_places=2)] = Field(None, description="Other fees")


    facilities: Optional[List[str]] = Field(None, description="List of facilities (e.g., Running Water, Power Supply)")
    amenities: Optional[List[str]] = Field(None, description="List of amenities (e.g., Swimming Pool, Gym)")
    
    listing_by: constr(max_length=50) = Field(..., description="Listed by (owner/agent)")
    