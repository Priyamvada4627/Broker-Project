from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional,Literal,List


class Agent_In(BaseModel):
    email: EmailStr
    password: str
    phone: str
    fee_percent: float
    min_fee: int
    max_fee: int
    city: str  
    name: str
    class Config:
        from_attributes = True
