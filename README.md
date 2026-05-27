# AW Client Report Portal

Internal web portal for generating quarterly **SACS** (Simple Automated Cashflow System) and **TCC** (Total Client Chart / net worth) PDF reports for client meetings.

Replaces the current full-day manual process (pulling balances from Pinnacle, Schwab, Zillow, RightCapital; assembling in Canva + Word; hand-calculating totals) with a single portal where the team enters balances into a structured form and downloads polished PDFs in minutes.

## What it does

- **Client management** — one-time profile entry per client (names, DOB, SSN-last4, salaries, expense budget, deductibles, account floor), plus a list of their accounts (retirement, non-retirement, trust, liabilities)
- **Quarterly report data entry** — pre-filled form with last-quarter balances, "use last value" buttons, live-calculated totals in the sidebar, submit disabled until all required balances are filled
- **Automated math** — Inflow/Outflow/Excess, Private Reserve target (6× monthly outflow + insurance deductibles), per-spouse retirement totals, non-retirement total, grand-total net worth (= retirement + non-retirement + trust), liabilities shown separately (never subtracted from net worth)
- **PDF generation** — 2-page SACS (Monthly Cashflow + Long Term Cashflow) and a landscape TCC, matching the existing visual templates with pixel-stable layout
- **Stale-data marker** — any balance whose as-of date is earlier than the report date renders with a `*` and the legend "* Indicates we do not have up to date information"
- **Report history** — every generated report is snapshotted, so re-downloading an old PDF gives the exact same numbers even after account balances change

## Stack

- **Backend:** Python 3.11+ / Flask 3
- **Database:** SQLite (file-based — minimal volume, ~6 clients)
- **PDF:** ReportLab (pure Python, no system dependencies)
- **Frontend:** Vanilla HTML/CSS/JS (server-rendered Jinja2 templates)
- **Auth:** Single shared password via env var

No external API integrations in V1 — all balances entered manually. RightCapital/Schwab/Pinnacle/Zillow auto-pull is V2.

## Local setup

```powershell
# 1. Install deps
pip install -r requirements.txt

# 2. Configure
copy .env.example .env
# Edit .env and set PORTAL_PASSWORD and SECRET_KEY

# 3. (optional) Seed the Sample Client from the TCC reference screenshot
python -m db.seed_sample

# 4. Run
python app.py
# → portal at http://127.0.0.1:5000
```

Log in with the shared password from `.env`.

## Project layout

```
.
├── app.py                      Flask app factory + route registration
├── config.py                   Env-driven config
├── requirements.txt
├── Dockerfile, railway.json    Ready to deploy (not yet deployed)
├── db/
│   ├── schema.sql              All DDL (clients, accounts, reports)
│   └── seed_sample.py          Loads the Sample Client from the TCC reference
├── models/
│   ├── database.py             SQLite connection helper, init_db()
│   ├── client.py               Client dataclass + CRUD
│   ├── account.py              Account dataclass + CRUD, pre-seeded account types
│   └── report.py               Report dataclass + CRUD, JSON snapshot storage
├── routes/
│   ├── auth.py                 /login, /logout, login_required decorator
│   ├── clients.py              Client CRUD + account management
│   └── reports.py              Report generation + PDF download
├── services/
│   ├── calculations.py         Pure SACS + TCC math (run `python -m services.calculations` for self-test)
│   └── pdf_generator.py        ReportLab drawing for SACS (2 pages) + TCC
├── templates/
│   ├── base.html, login.html
│   ├── clients/
│   │   ├── list.html
│   │   ├── form.html           Shared new/edit form
│   │   └── detail.html         Profile + accounts + report history
│   └── reports/
│       └── generate.html       Quarterly data entry form
├── static/
│   ├── css/app.css
│   └── js/report_form.js       Live-calc totals + missing-field highlighting
└── data/
    └── portal.db               SQLite file (gitignored, auto-created)
```

## End-to-end verification

1. `pip install -r requirements.txt`
2. `python -m db.seed_sample` — loads the Sample Client from the TCC reference screenshot (~6 retirement accounts, 7 non-retirement, 1 trust, 7 liabilities)
3. `python app.py`
4. Visit `http://127.0.0.1:5000`, log in with `.env`'s `PORTAL_PASSWORD`
5. Click "Sample Client 1 & Sample Client 2" → confirm:
   - **Grand Total: $326,620.89** (matches the reference screenshot — there's a ~$10 rounding tolerance on Wells Fargo Savings)
   - **Liabilities: $416,050.07** (matches exactly)
6. Click "Generate Report" → form pre-fills with last balances. Live sidebar totals update as you type.
7. Submit → downloads both PDFs from the client detail page
8. Compare PDFs visually to the reference templates: green Inflow / red Outflow / blue Private Reserve circles on SACS p1, FICA + Investment on SACS p2, account bubbles arranged by quadrant on TCC.

## Calculation rules (per the discovery transcript)

- **SACS Excess** = Inflow − Outflow (drives monthly contribution to Private Reserve)
- **SACS Target** = 6 × monthly Outflow + total insurance deductibles
- **TCC Non-Retirement Total** *excludes* the trust
- **TCC Grand Total** = Client 1 Retirement + Client 2 Retirement + Non-Retirement + Trust
- **TCC Liabilities** are shown separately, *never* subtracted from net worth
- The **$1,000 floor** in each bank account is a constant, not entered per report

Pure functions in `services/calculations.py` — run `python -m services.calculations` to validate against the Sample Client numbers.

## Out of scope (V2)

- Auto-pull from RightCapital / Schwab / Pinnacle / Zillow
- Canva export
- Dropbox auto-save of generated PDFs
- Monthly email distribution to clients
- Client-facing expense worksheet
- Onboarding automation agent
- Multi-user authentication
- Actual Railway deployment
