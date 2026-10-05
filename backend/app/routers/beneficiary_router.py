from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.beneficiary import BeneficiaryRiskProfile
from app.schemas.transaction_schemas import BeneficiaryCheckResult

router = APIRouter(prefix="/api/beneficiaries", tags=["beneficiaries"])

WARNING_MESSAGES = {
    "WATCHLISTED": (
        "This recipient account has been associated with suspicious "
        "transaction activity. Please verify the recipient before proceeding."
    ),
    "HIGH_RISK": (
        "Warning: this recipient account has multiple confirmed fraud "
        "reports and is strongly associated with scam activity. We "
        "strongly recommend you do not proceed with this transfer."
    ),
}


@router.get("/check", response_model=BeneficiaryCheckResult)
def check_beneficiary(account_number: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = (
        db.query(BeneficiaryRiskProfile)
        .filter(BeneficiaryRiskProfile.account_number == account_number)
        .first()
    )
    if not profile:
        return BeneficiaryCheckResult(account_number=account_number, risk_category="UNKNOWN")

    category = profile.risk_category.value
    return BeneficiaryCheckResult(
        account_number=account_number,
        risk_category=category,
        warning_message=WARNING_MESSAGES.get(category),
        tags=profile.tags or [],
    )
