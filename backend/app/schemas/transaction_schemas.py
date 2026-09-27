from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class TransactionCreate(BaseModel):
    recipient_account_number: str = Field(min_length=10, max_length=10)
    recipient_name: Optional[str] = None
    recipient_bank: Optional[str] = "FinGuard Bank"
    amount: Decimal = Field(gt=0)
    transaction_type: str = "transfer"
    narration: Optional[str] = None

    # Context sent by the frontend (captured from browser/device)
    device_fingerprint: str
    browser: Optional[str] = None
    operating_system: Optional[str] = None
    ip_address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Nigeria"

    # For demo/hackathon scenarios: allow overriding the "current time" so
    # a judge can trigger a 3AM scenario during a daytime demo.
    simulated_hour: Optional[int] = Field(default=None, ge=0, le=23)


class TransactionResult(BaseModel):
    transaction_id: str
    reference: str
    status: str
    risk_level: Optional[str] = None
    customer_message: str
    requires_otp: bool = False
    requires_verification: bool = False


class TransactionOut(BaseModel):
    id: str
    reference: str
    recipient_account_number: str
    recipient_name: Optional[str]
    amount: Decimal
    transaction_type: str
    status: str
    risk_level: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class OTPVerifyRequest(BaseModel):
    transaction_id: str
    otp_code: str


class FacialVerifyRequest(BaseModel):
    transaction_id: str
    descriptor: List[float] = Field(min_length=128, max_length=128)


class FaceEnrollRequest(BaseModel):
    descriptor: List[float] = Field(min_length=128, max_length=128)