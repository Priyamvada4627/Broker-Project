from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email:EmailStr
    password:str
    phone:str

class UserOut(BaseModel):
    id: int
    email:EmailStr
    created_at: datetime
    phone: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token:str
    token_type:str

class TokenData(BaseModel):
    id:Optional[int]=None


    