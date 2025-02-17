from typing import List
from pydantic import BaseModel

class Ward(BaseModel):
    name: str

class LGA(BaseModel):
    name: str
    wards: List[str]

class State(BaseModel):
    name: str
    lgas: List[LGA]

# MongoDB Schema
state_schema = {
    "name": "string",
    "lgas": [
        {
            "name": "string",
            "wards": ["string"]
        }
    ]
} 
