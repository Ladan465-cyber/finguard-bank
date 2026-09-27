# Demo Scenario Scoring Reference

The seed script (`backend/app/seed.py`) builds Ngozi Chukwu's 18-transaction
history using **fixed random seeds**, so her computed behaviour profile is
identical every time you run `python -m app.seed`:

- **Average transaction amount:** ₦26,311.33
- **Max transaction amount:** ₦49,453
- **Typical hours:** roughly 08:00–21:00
- **Known recipients:** Chinedu Okafor (`1011112222`), Amaka Eze (`1022223333`)
- **Known city:** Lagos
- **Known device:** trusted (used 25 times)

The four demo buttons on the Transfer page are calibrated against this
exact baseline. Here's the math FinShield actually runs for each one
(see `backend/app/services/fraud_engine.py::score_transaction`):

## Scenario A — LOW (expected: instant approval)
- Amount ₦20,000 → ratio to average = 0.76x → **no amount trigger** (below 2x)
- Known recipient, known device, known city → **no triggers**
- **Score: 0 → LOW**

## Scenario B — MEDIUM (expected: OTP required)
- Amount ₦90,000 → ratio = 3.42x → *"moderately above normal range"* (+15)
- New recipient (Tunde Bakare, `1033334444`) → *"new recipient detected"* (+12)
- **Score: 27 → MEDIUM** (20–44 band)

## Scenario C — HIGH (expected: identity verification required)
- Amount ₦70,000 → ratio = 2.66x → *"moderately above normal range"* (+15)
- New device (fingerprint reset before sending) → *"unrecognised device"* (+20)
- Unusual city, Kano vs. known Lagos → *"unusual location"* (+18)
- 3 independent anomalies triggered together → combo bonus (+15)
- **Score: 68 → HIGH** (45–74 band)

## Scenario D — CRITICAL (expected: blocked + fraud alert)
- Amount ₦600,000 → ratio = 22.8x (also > 1.5x the historical max) →
  *"extremely above normal range"* (+45)
- New recipient (Unknown Wallet Services, `1099998888`) → (+12)
- New device → (+20)
- Unusual city (Kano) → (+18)
- Unusual time (03:00, outside the 08:00–21:00 typical window) → (+10)
- 5 anomalies triggered together → combo bonus (+15)
- Raw total 120, **capped at 100 → CRITICAL** (≥75 band)

---

### Why these specific amounts (not the illustrative ₦500,000 from the brief)?

The original brief's example numbers (e.g. "₦500,000 from a new device")
are useful for explaining the *concept*, but because risk scoring is
multiplicative across triggered rules, that exact amount combined with a
new device AND unusual location would actually push the score into
CRITICAL, not HIGH, given this dataset's average. The demo amounts above
were chosen specifically so each button reliably lands on its **intended**
tier — useful for a live presentation where you don't want an occasional
wrong classification. You're welcome to try other amounts live (the amount
field is fully editable) to show the score moving between tiers in
real time.

### Rule weights are not hardcoded

All weights above live in the `fraud_rules` MySQL table (seeded from
`DEFAULT_RULE_WEIGHTS` in `fraud_engine.py`) and are re-read on every
transaction. You can open MySQL and change a weight (e.g. lower
`new_device` from 20 to 10) and immediately see live transactions score
differently — a nice thing to demonstrate live if a judge asks whether the
rules are configurable.
