from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str = Field(min_length=6)
    home_city: str = "Lagos"


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    device_fingerprint: str
    browser: Optional[str] = None
    operating_system: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Nigeria"


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: str


class UserProfileOut(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str
    home_city: Optional[str]
    home_country: Optional[str]
    status: str

    class Config:
        from_attributes = True
