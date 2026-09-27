"""
Seeds the FinGuard database with realistic Nigerian fintech demo data.

Run with:  python -m app.seed   (from the backend/ directory, venv active)

Creates:
- Fraud rule weights (configurable, not hardcoded in the engine)
- 1 admin user
- 3 demo customers with real transaction HISTORY so their behaviour
  profiles are genuinely learned, not hand-set
- A pre-existing blocked/critical transaction + fraud alert so the admin
  dashboard has something to show immediately
"""
import random
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import SessionLocal, Base, engine
from app import models  # noqa
from app.models.user import User, AdminUser, UserStatus, AdminRole
from app.models.account import Account
from app.models.device import Device
from app.models.transaction import Transaction, TransactionStatus, RiskLevel, TransactionType
from app.models.fraud import FraudRule, FraudEvent, FraudEventStatus
from app.auth.security import hash_password
from app.services.fraud_engine import DEFAULT_RULE_WEIGHTS
from app.services.behavior_service import refresh_behavior_profile

Base.metadata.create_all(bind=engine)
db = SessionLocal()

DEMO_DEVICE_LAGOS = "fp_demo_lagos_chrome_win_001"
LAGOS = {"city": "Lagos", "country": "Nigeria"}


def reset_transactional_data():
    """Clears prior demo data so the script is safely re-runnable."""
    db.query(FraudEvent).delete()
    db.query(Transaction).delete()
    db.query(Device).delete()
    db.query(models.UserBehaviorProfile).delete()
    db.query(Account).delete()
    db.query(User).delete()
    db.query(AdminUser).delete()
    db.query(FraudRule).delete()
    db.commit()


def seed_fraud_rules():
    for key, weight in DEFAULT_RULE_WEIGHTS.items():
        db.add(FraudRule(rule_key=key, description=key.replace("_", " ").capitalize(),
                          weight=Decimal(str(weight)), is_active=True, version="1.0.0"))
    db.commit()


def seed_admin():
    admin = AdminUser(
        full_name="Adaeze Fraud Analyst",
        email="admin@finguard.ng",
        password_hash=hash_password("Admin@123"),
        role=AdminRole.super_admin,
    )
    db.add(admin)
    db.commit()


def make_user(full_name, email, phone, city, balance, account_number):
    user = User(
        full_name=full_name, email=email, phone=phone,
        password_hash=hash_password("Demo@123"),
        status=UserStatus.active, home_city=city, home_country="Nigeria",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    account = Account(user_id=user.id, account_number=account_number, balance=Decimal(str(balance)))
    db.add(account)
    db.commit()
    return user, account


def add_completed_transaction(sender: User, sender_acc: Account, recipient_acc: Account, recipient_name,
                               amount, days_ago, hour, device_fp, city, country="Nigeria"):
    created = datetime.utcnow() - timedelta(days=days_ago)
    created = created.replace(hour=hour, minute=random.randint(0, 59))
    txn = Transaction(
        reference="FGX" + "".join(random.choices("0123456789", k=10)),
        sender_id=sender.id,
        sender_account_number=sender_acc.account_number,
        recipient_account_number=recipient_acc.account_number,
        recipient_name=recipient_name,
        recipient_bank="FinGuard Bank",
        amount=Decimal(str(amount)),
        transaction_type=TransactionType.transfer,
        narration="Demo history",
        device_fingerprint=device_fp,
        browser="Chrome 128",
        operating_system="Windows 11",
        ip_address="105.112.10.24",
        city=city,
        country=country,
        risk_level=RiskLevel.low,
        risk_score=Decimal("5.0"),
        risk_factors=["No anomalies detected — transaction matches user's established behaviour"],
        fraud_rule_version="1.0.0",
        status=TransactionStatus.completed,
        created_at=created,
        completed_at=created,
    )
    db.add(txn)
    db.commit()


def seed_primary_demo_user_with_history():
    """
    Ngozi Chukwu: the main character of the demo. She has ~20 days of
    normal history so her behaviour profile is realistic:
      - Normal range: ~10,000 - 50,000
      - Always from Lagos, same device
      - Transacts between 8am and 9pm
      - Sends mostly to 2 known recipients
    """
    ngozi, ngozi_acc = make_user(
        "Ngozi Chukwu", "ngozi.chukwu@example.com", "+2348031234567",
        "Lagos", 750_000, "1023456789",
    )

    # trust the device via two logins-worth of use
    device = Device(
        user_id=ngozi.id, device_fingerprint=DEMO_DEVICE_LAGOS,
        browser="Chrome 128", operating_system="Windows 11",
        is_trusted=True, times_used=25,
        first_seen_at=datetime.utcnow() - timedelta(days=40),
        last_seen_at=datetime.utcnow() - timedelta(days=1),
    )
    db.add(device)
    db.commit()

    # known recipients: her landlord (Chinedu) and her sister (Amaka)
    landlord, landlord_acc = make_user(
        "Chinedu Okafor", "chinedu.okafor@example.com", "+2348022223333",
        "Lagos", 200_000, "1011112222",
    )
    sister, sister_acc = make_user(
        "Amaka Eze", "amaka.eze@example.com", "+2348033334444",
        "Abuja", 120_000, "1022223333",
    )

    # Dedicated RNG streams (fixed seeds) so the resulting average/typical
    # amounts are exactly reproducible every time the seed script runs --
    # this is what lets the hackathon demo scenario buttons reliably land
    # on their intended risk tier (see documentation/DEMO_SCENARIOS.md).
    rng_amount = random.Random(42)
    rng_recipient = random.Random(7)
    rng_hour = random.Random(13)

    for i in range(18):
        recipient_acc, recipient_name = rng_recipient.choice(
            [(landlord_acc, "Chinedu Okafor"), (sister_acc, "Amaka Eze")]
        )
        amount = rng_amount.randint(10_000, 50_000)
        hour = rng_hour.randint(8, 21)
        add_completed_transaction(
            ngozi, ngozi_acc, recipient_acc, recipient_name, amount,
            days_ago=20 - i, hour=hour, device_fp=DEMO_DEVICE_LAGOS, city="Lagos",
        )

    refresh_behavior_profile(db, ngozi.id)
    return ngozi, ngozi_acc, landlord_acc, sister_acc


def seed_secondary_users():
    """A couple of extra accounts so recipients can be typed in during the
    HIGH / CRITICAL scenarios (new, unrecognised recipients for Ngozi)."""
    make_user("Tunde Bakare", "tunde.bakare@example.com", "+2348044445555",
              "Port Harcourt", 60_000, "1033334444")
    make_user("Unknown Wallet Services", "wallet@unknownexchange.example", "+2348099998888",
              "Lagos", 0, "1099998888")


def seed_preexisting_fraud_alert(ngozi, ngozi_acc):
    """A CRITICAL transaction from two days ago so the admin dashboard
    isn't empty the moment a judge opens it."""
    created = datetime.utcnow() - timedelta(days=2, hours=3)
    txn = Transaction(
        reference="FGX" + "".join(random.choices("0123456789", k=10)),
        sender_id=ngozi.id,
        sender_account_number=ngozi_acc.account_number,
        recipient_account_number="1099998888",
        recipient_name="Unknown Wallet Services",
        recipient_bank="FinGuard Bank",
        amount=Decimal("650000"),
        transaction_type=TransactionType.transfer,
        narration="urgent",
        device_fingerprint="fp_unknown_device_kano_999",
        browser="Firefox 118 (Android)",
        operating_system="Android 13",
        ip_address="41.58.12.9",
        city="Kano",
        country="Nigeria",
        risk_level=RiskLevel.critical,
        risk_score=Decimal("91.0"),
        risk_factors=[
            "Transaction amount is extremely above the user's normal range (18.5x average)",
            "New recipient detected (not in user's known recipient list)",
            "Transaction initiated from an unrecognised device",
            "Transaction originates from a location not previously used by this user",
            "Transaction occurred at an unusual time (03:00)",
            "Multiple independent risk indicators triggered simultaneously",
        ],
        fraud_rule_version="1.0.0",
        status=TransactionStatus.blocked,
        investigation_status="open",
        created_at=created,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    db.add(FraudEvent(
        transaction_id=txn.id, user_id=ngozi.id,
        risk_level="CRITICAL", risk_score=Decimal("91.0"),
        risk_factors=txn.risk_factors, fraud_rule_version="1.0.0",
        status=FraudEventStatus.open, created_at=created,
    ))
    db.commit()


def main():
    print("Resetting demo data...")
    reset_transactional_data()
    print("Seeding fraud rules...")
    seed_fraud_rules()
    print("Seeding admin user...")
    seed_admin()
    print("Seeding primary demo user (Ngozi Chukwu) with 18 days of history...")
    ngozi, ngozi_acc, landlord_acc, sister_acc = seed_primary_demo_user_with_history()
    print("Seeding secondary demo users (for new-recipient scenarios)...")
    seed_secondary_users()
    print("Seeding a pre-existing CRITICAL fraud alert for the admin dashboard...")
    seed_preexisting_fraud_alert(ngozi, ngozi_acc)

    print("\nDone! Demo credentials:")
    print("  Customer login : ngozi.chukwu@example.com / Demo@123")
    print("  Admin login    : admin@finguard.ng / Admin@123")
    print(f"  Ngozi's known recipient (landlord) account number : {landlord_acc.account_number}")
    print(f"  Ngozi's known recipient (sister) account number   : {sister_acc.account_number}")
    print("  Unknown recipient account number for demos          : 1033334444 (Tunde Bakare)")


if __name__ == "__main__":
    main()
