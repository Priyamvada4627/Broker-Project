from pydantic import BaseModel
from datetime import datetime
from backend.schemas.bid import SellerInterestOut
from enum import Enum
from typing import Optional

class PropertyPurpose(str, Enum):
    buy = "buy"
    rent = "rent"

class PropertyType(str, Enum):
    apartment = "apartment"
    house = "house"
    flat="flat"
    plot = "plot"
    commercial = "commercial"

class LocationIn(BaseModel):
    city: str
    state: str
    pincode: str

class PropertyIn(BaseModel):
    description: str
    city: str
    state: str
    pincode: str
    price: int
    property_type: PropertyType
    purpose: PropertyPurpose
    is_available: bool = True
    bedrooms: Optional[int] = 2
    bathrooms: Optional[int] = 2
    area: Optional[float] = 1000.0

class SellerInterest(BaseModel):
    id: int
    property_id: int
    bid_amount: int | None
    counter_amount: int | None
    status: str

    class Config:
        from_attributes = True

class LocationOut(BaseModel):
    city: str
    state: str
    pincode: str

    class Config:
        from_attributes = True

class SellerPropertyOut(BaseModel):
    id: int
    description: str
    location: LocationOut
    price: int
    property_type: str
    purpose: str
    is_available: bool
    is_verified: bool
    verification_status: str
    remarks: Optional[str] = None
    interests: list[SellerInterest] = []
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area: Optional[float] = None
    class Config:
        from_attributes = True


class BuyerPropertyOut(BaseModel):
    property_id: int
    description: str
    location: LocationOut
    price_to_pay: int
    is_available: bool
    ml_estimate: Optional[int] = None       
    ml_price_range: Optional[dict] = None   
    ml_confidence: Optional[str] = None     
    class Config:
        from_attributes = True

class PropertyUpdate(BaseModel):
    price: Optional[int] = None
    description: Optional[str] = None
    property_type: Optional[PropertyType] = None
    purpose: Optional[PropertyPurpose] = None