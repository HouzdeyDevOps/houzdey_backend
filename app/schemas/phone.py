from pydantic import BaseModel, Field
from typing import Optional

class PhoneNumberRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number in international format")

class VerifyOTPRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to verify")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")

class PhoneResponse(BaseModel):
    message: str
    status: str = Field(default="success", description="Response status") 