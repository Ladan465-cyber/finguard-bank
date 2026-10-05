# Demo Scenario Reference -- FinShield v2 (Multi-Layer Engine)

FinShield's decision engine reads FOUR independent layers -- Customer
Behaviour, Device & Location, Transaction Context, and Beneficiary Risk --
through an explicit, ordered rule table (see
`backend/app/services/fraud_engine.py::decide()`). Nothing is added up
into a score; each rule is a plain condition, checked top to bottom, first
match wins.

Ngozi Chukwu's seeded history (`python -m app.seed`, fixed random seeds)
gives her a genuine baseline:
- **Average transaction amount:** ~₦26,311
- **Known recipients:** Chinedu Okafor (`1011112222`), Amaka Eze (`1022223333`)
- **Known device & city:** trusted device, Lagos
- **Watchlisted recipient:** `1099998888` (Unknown Wallet Services) --
  seeded as **HIGH_RISK**, tagged `ponzi_scheme`, `multiple_fraud_reports`,
  `mule_account`

## Scenario 1 -- SAFE
Known recipient, known device, ₦20,000, normal city.
All four layers report their best value -> **Rule 8 -> SAFE**. Instant approval.

## Scenario 2 -- VERIFY
New recipient (Tunde Bakare, `1033334444`), ₦150,000, known device/city.
- Behaviour: ratio ~5.7x average -> `MEDIUM_CONCERN`
- Context: `NEW_BENEFICIARY_LARGE_AMOUNT` flag fires
- Beneficiary: `UNKNOWN` (no watchlist entry)
-> **Rule 6 -> VERIFY** (OTP required)

## Scenario 3 -- Beneficiary warning, then HIGH_RISK
Watchlisted recipient (`1099998888`), otherwise ordinary transaction
(₦20,000, known device, Lagos).
- The moment this account number is entered, the frontend calls
  `GET /api/beneficiaries/check` and shows the OPay-style warning modal
  **before** the transaction is even submitted.
- If the customer clicks **Proceed Anyway**: Beneficiary=`HIGH_RISK`, no
  other layer concerned -> **Rule 2 -> HIGH_RISK** (OTP, then facial verification)

## Scenario 4 -- New device + risky recipient
Same watchlisted recipient, but from a reset (new) device, in Kano
(unfamiliar city), ₦40,000.
- Device & Location: new device + unfamiliar city -> `SUSPICIOUS`
- Beneficiary: `HIGH_RISK`
- Only 1 other layer concerned (Device), not 2+, so Rule 1's escalation
  condition isn't met -> **Rule 2 -> HIGH_RISK** (OTP, then facial verification)

## Scenario 5 -- CRITICAL
Same watchlisted recipient, new device, Kano, ₦600,000, simulated 3AM.
- Behaviour: ratio ~22.8x average (and beyond 1.5x historical max) -> `HIGH_CONCERN`
- Device & Location: new device + unfamiliar city -> `SUSPICIOUS`
- Context: `UNUSUAL_TIME` and `SPENDING_SPIKE` flags fire
- Beneficiary: `HIGH_RISK`
- That's 3 other layers concerned (>= `CONCERN_ESCALATION_COUNT` of 2)
-> **Rule 1 -> CRITICAL**. Blocked instantly, fraud alert created.

---

## Why these specific numbers

Behaviour tier thresholds are relative to each user's own average (not
fixed Naira amounts), so they generalise to any user's spending pattern.
The exact amounts above were chosen to reliably land on their intended
tier given Ngozi's seeded ~₦26,311 average -- if you change the seed data,
re-derive these from `behaviour_tier()`'s ratio thresholds in
`fraud_engine.py` (2x / 4x / 8x average, or 1.5x historical max).

## Rule weights are not hardcoded numbers -- they're named constants

`VELOCITY_WINDOW_MINUTES`, `VELOCITY_TRANSACTION_THRESHOLD`, and
`CONCERN_ESCALATION_COUNT` at the top of `fraud_engine.py` are the only
"dials" in the whole system, and each has an obvious real-world meaning
(unlike an arbitrary point value). Changing `CONCERN_ESCALATION_COUNT`
from 2 to 3, for example, makes Rule 1 harder to trigger -- fewer
transactions would escalate all the way to CRITICAL.

## Managing the watchlist live, during a demo

Log into the admin console and open **Beneficiaries** in the nav bar. You
can add, edit, or remove watchlist entries there in real time -- a good
thing to demonstrate live: add a brand-new account to the watchlist, then
immediately show a transfer to that account triggering the warning modal.
