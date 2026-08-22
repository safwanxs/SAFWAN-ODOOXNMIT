# Dayflow — Human Resource Management System

Repo: https://github.com/safwanxs/SAFWAN-ODOOXNMIT

## Problem statement and approach

HR teams commonly manage employee identity, attendance, leave, and payroll in separate tools. Dayflow brings those workflows into one FastAPI application: administrator-provisioned accounts, employee self-service, attendance reporting, leave approval, and an attendance-linked payroll preview.

## Stack

FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL (production), SQLite (local development), JWT, Pydantic v2, Jinja2, Chart.js, and pytest.

## Progress

- [x] Phase 1: Foundation, database design, admin-provisioned authentication, and role-based access
- [x] Phase 2: Employee directory, profiles, salary access controls, and attendance
- [x] Phase 3: Role-specific attendance reporting with server-computed hours
- [x] Phase 4: Leave and time-off management, allocations, approvals, certificates, and attendance integration
- [x] Phase 5: Attendance-linked payroll engine, analytics dashboard, final validation, and deployment configuration

## Database design choices

- `users` has unique indexed email and login ID fields plus a composite company/year/serial constraint for generated employee IDs. Accounts are soft-deleted with `is_active`.
- Attendance is constrained to one record per user per date. Leave allocation is unique per employee and leave type, preventing duplicate allocation rows.
- Salary structures, employee profiles, leave requests, and attendance remain separate from authentication identity records. This keeps sensitive salary data behind admin-only APIs.

## Differentiator: payroll readiness preview

The payroll preview is calculated from real data, not manually entered payable days. It excludes public holidays, subtracts approved unpaid leave and missing attendance, includes approved paid/sick leave, prorates pay, and shows PF and professional-tax deductions. Employees can view only their own preview; administrators can review any employee's.

## Security

Employees are provisioned by an administrator and must change their one-time temporary password on first login. Passwords are bcrypt hashed; JWTs contain only identity/role/expiry. ORM queries are parameterized—there is no raw SQL string formatting. `.env` is ignored, and login injection input such as `' OR 1=1` is rejected as an invalid identifier/password.

## Setup

```bash
git clone https://github.com/safwanxs/SAFWAN-ODOOXNMIT.git
cd SAFWAN-ODOOXNMIT
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Set `DATABASE_URL` to PostgreSQL and a strong `SECRET_KEY` for deployment.

## Deploy

`render.yaml` configures a Render web service. Create a Render PostgreSQL database, set its connection string as `DATABASE_URL`, then deploy the repository. The build command runs `alembic upgrade head` and the start command launches Uvicorn.

- Live link: pending deployment (requires the project owner's Render/Railway account)
- Demo video: pending recording (requires a deployed public link)

## Verification

```bash
pytest -q
```

## Honest limitation

Payroll is an on-demand calculation preview; this hackathon version does not yet create immutable payroll-run records, support statutory rules for every jurisdiction, or send payslips.