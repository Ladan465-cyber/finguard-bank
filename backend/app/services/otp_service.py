"""
Simulated OTP provider for the hackathon demo.

In production this module's `send_otp()` would call a real SMS/voice API
(Termii, Twilio, AWS SNS...). The interface is deliberately provider-
agnostic so swapping it later doesn't touch the fraud engine or routers.
"""
import random
from datetime import datetime, timedelta

from app.auth.security import hash_password, verify_password
from app.core.config import settings


def generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def hash_otp(code: str) -> str:
    return hash_password(code)


def verify_otp(code: str, code_hash: str) -> bool:
    return verify_password(code, code_hash)


def otp_expiry() -> datetime:
    return datetime.utcnow() + timedelta(seconds=settings.OTP_EXPIRE_SECONDS)


def demo_deliver(otp_code: str, phone: str) -> str:
    """
    'Sends' the OTP. In demo mode we don't hit a real SMS gateway -- we
    return the code so the frontend can display it in a clearly-labelled
    'Demo mode' banner (standard practice for hackathon fintech demos).
    """
    if settings.OTP_DEMO_MODE:
        return otp_code
    # Real provider integration would go here.
    return ""
