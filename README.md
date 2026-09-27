# FinGuard Bank — FinShield Fraud Detection Demo

A full-stack digital banking prototype where **every transaction is screened
in real time by FinShield**, a transparent, behaviour-based fraud detection
engine — before it's allowed to complete.

```
frontend/        React + Vite customer & admin apps
backend/          FastAPI API + FinShield fraud engine
database/        MySQL schema reference (auto-created by the backend too)
documentation/    Architecture notes, demo script, ML roadmap
```

This guide assumes **no prior backend/frontend experience**. Follow it top
to bottom.

---

## 0. What you need installed

| Tool | Why | Check you have it |
|---|---|---|
| Python 3.10+ | Runs the backend | `python --version` (or `python3 --version`) |
| Node.js 18+ | Runs the frontend | `node --version` |
| MySQL 8 (via **XAMPP** or a standalone MySQL install) | Stores all data | see below |

### If you're using XAMPP (common on Windows for beginners)
1. Open the **XAMPP Control Panel**.
2. Click **Start** next to **MySQL** (and **Apache** if you want phpMyAdmin's UI).
3. Your MySQL server is now running on `localhost:3306` with username `root`
   and (by default) **no password**.
4. You do NOT need Apache/PHP for this project — only the MySQL service.

### If you have standalone MySQL installed
Just make sure the MySQL service is running and you know your `root`
password (or another user's credentials).

---

## 1. Get the database ready

You have two options — pick one.

**Option A — let the backend create it automatically (easiest).**
Just create an empty database; the backend will create all the tables for
you on first run.

Open phpMyAdmin (`http://localhost/phpmyadmin` if using XAMPP) or a MySQL
client, and run:
```sql
CREATE DATABASE finguard_db;
```

**Option B — run the full schema file yourself** (if you prefer to see the
exact SQL):
```bash
mysql -u root -p < database/schema.sql
```
(Leave the password blank/press Enter if your XAMPP MySQL has no password.)

---

## 2. Set up the backend (FastAPI)

Open a terminal **in the `backend/` folder**:

```bash
cd backend
```

### 2.1 Create a virtual environment
```bash
python -m venv venv
```

Activate it:
- **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
- **Windows (cmd):** `venv\Scripts\activate.bat`
- **Mac/Linux:** `source venv/bin/activate`

You should now see `(venv)` at the start of your terminal prompt.

### 2.2 Install dependencies
```bash
pip install -r requirements.txt
```

### 2.3 Configure environment variables
Copy the example file:
- **Windows:** `copy .env.example .env`
- **Mac/Linux:** `cp .env.example .env`

Open the new `.env` file in a text editor and set:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=          <- leave blank if XAMPP MySQL has no password
DB_NAME=finguard_db
JWT_SECRET_KEY=        <- put any long random string here
```

To generate a good random secret, run:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
and paste the output as `JWT_SECRET_KEY`.

### 2.4 Start the backend
```bash
uvicorn app.main:app --reload
```
You should see something like `Uvicorn running on http://127.0.0.1:8000`.
Leave this terminal running.

Visit **http://localhost:8000/docs** in your browser — you should see the
interactive API documentation (Swagger UI). If you see this, your backend
is working. ✅

### 2.5 Load the demo data
Open a **second terminal**, go into `backend/`, activate the venv again
(same commands as 2.1), and run:
```bash
python -m app.seed
```
This creates:
- an admin account
- a demo customer (**Ngozi Chukwu**) with 18 days of realistic transaction
  history already loaded, so FinShield has a genuine behaviour baseline
- a couple of extra accounts used as transfer recipients in the demo
- a pre-existing blocked/critical transaction so the admin dashboard isn't
  empty the first time you open it

You'll see printed demo credentials at the end — keep that terminal output
visible for your presentation.

You can re-run `python -m app.seed` any time to reset the demo data back to
a clean state.

---

## 3. Set up the frontend (React + Vite)

Open a **third terminal**, in the project's `frontend/` folder:

```bash
cd frontend
npm install
```

Copy the environment file:
- **Windows:** `copy .env.example .env`
- **Mac/Linux:** `cp .env.example .env`

The default `VITE_API_URL=http://localhost:8000` is correct if you followed
the steps above unchanged.

Start the frontend:
```bash
npm run dev
```
Visit **http://localhost:5173** — you should see the FinGuard Bank login
screen. ✅

---

## 4. Demo credentials

| Role | Email | Password |
|---|---|---|
| Customer | `ngozi.chukwu@example.com` | `Demo@123` |
| Admin | `admin@finguard.ng` | `Admin@123` |

Admin console: click **"Admin console →"** on the login screen, or go
directly to `http://localhost:5173/admin/login`.

---

## 5. Running the hackathon demo

Log in as the demo customer and go to **Transfer**. There's a
**"🎬 Hackathon demo scenarios"** panel with four one-click presets:

| Button | What it does | Expected result |
|---|---|---|
| **Scenario A** | Known recipient, known device, ₦20,000 | ✅ **LOW** — instant success |
| **Scenario B** | New recipient, ₦90,000 | 🟡 **MEDIUM** — OTP required (shown on screen in demo mode) |
| **Scenario C** | Known recipient, new device, new city (Kano), ₦70,000 | 🟠 **HIGH** — simulated identity/facial verification required |
| **Scenario D** | New recipient, new device, new city, 3AM, ₦600,000 | 🔴 **CRITICAL** — blocked instantly + fraud alert created |

Click a preset, then click **"Send transfer"** to actually trigger it. For
Scenario B you'll see the demo OTP code displayed right on screen (no real
SMS is sent — clearly labelled "Demo mode"). For Scenario C, click
**"Simulate successful scan"** or **"Simulate failed scan"** to see both
outcomes.

Then switch to the **admin console** (`admin@finguard.ng` / `Admin@123`)
and show:
- **Overview** — live stats updating as you trigger scenarios
- **Transactions** — click any row to see the full risk breakdown (exact
  triggered indicators, risk score, device, location)
- **Fraud Alerts** — resolve the Scenario D alert as "Confirmed fraud" or
  "Confirmed legitimate" live, in front of the judges
- **Audit Logs** — show the tamper-evident trail of everything that happened

See `documentation/DEMO_SCENARIOS.md` for the exact math behind why each
scenario lands on its risk tier — useful if a judge asks "how does the
engine actually decide this?"

---

## 6. How the fraud engine actually works (for judges' Q&A)

FinShield is a **transparent, weighted rule engine** (not a black box, and
not random). For every transaction it:

1. Pulls the sender's **real behaviour profile** — computed from their own
   completed transaction history (average amount, typical range, common
   recipients, common cities, typical active hours) — see
   `backend/app/services/behavior_service.py`.
2. Extracts features comparing the new transaction against that profile:
   amount deviation, new recipient, new device, unusual location, unusual
   time, transaction frequency, balance utilisation — see
   `extract_features()` in `backend/app/services/fraud_engine.py`.
3. Scores each triggered rule using **configurable weights stored in the
   `fraud_rules` database table** (not hardcoded), plus a bonus when 3+
   independent anomalies fire together.
4. Maps the final 0–100 score to LOW / MEDIUM / HIGH / CRITICAL and records
   **exactly which factors fired**, so every decision is auditable.
5. The decision engine then approves, requires OTP, requires identity
   verification, or blocks + raises a fraud alert accordingly.

The architecture deliberately separates `extract_features()` from
`score_transaction()` so the rule engine can later be swapped for a trained
ML model without touching the API layer — see
`documentation/ML_ROADMAP.md`.

---

## 7. Troubleshooting

**"Can't connect to MySQL server"** — Make sure MySQL is actually running
(check the XAMPP Control Panel), and that `DB_HOST`/`DB_PORT`/`DB_USER`/
`DB_PASSWORD` in `backend/.env` match your setup.

**Backend starts but frontend shows network errors** — Check the backend
terminal is still running and showing no errors, and that
`frontend/.env`'s `VITE_API_URL` matches the backend's address
(`http://localhost:8000` by default).

**"relation/table doesn't exist" errors** — The backend creates tables
automatically on startup (`Base.metadata.create_all`), but only for tables
that don't already exist. If you manually ran `schema.sql` AND changed a
model, drop the database and let the backend recreate it, or re-run
`schema.sql` after dropping.

**Demo data looks wrong / scenarios don't match expected risk levels** —
Re-run `python -m app.seed`. It fully resets and rebuilds the demo dataset
using fixed random seeds, so it's always reproducible.

**Port already in use** — Something else is using port 8000 or 5173. Stop
that process, or run the backend with `uvicorn app.main:app --reload --port 8001`
(and update `VITE_API_URL` to match).
