# Dayflow — Human Resource Management System

**Live demo:** https://dayflow-hrms-jq5c.onrender.com
**Demo admin login:** `alex.rao@dayflowdemo.com` / `AdminPass123!`

Dayflow centralizes employee identity, attendance, leave, and payroll workflows in one HRMS application. It is built for fast operational visibility with role-based employee self-service and an administrator workspace.

## Features

- **Admin-provisioned authentication:** System-generated login IDs, JWT-backed sessions, and mandatory password change for provisioned employees.
- **Employee directory and profiles:** Searchable employee cards, role-aware profile access, salary privacy, and profile-picture upload for employees and administrators.
- **Attendance:** Check in/out actions with daily administrative reporting and employee monthly attendance views.
- **Leave and time off:** Employees request paid, sick, or unpaid leave; administrators approve or reject with comments; allocations update on approval.
- **Payroll preview — core differentiator:** Calculates payable days from attendance, public holidays, approved leave, and missing attendance. It prorates payroll and shows salary components, employee/employer PF, and professional tax.
- **CSV export:** Administrators can export payroll-ready employees (those with a salary structure) to CSV containing login ID, name, role, wage, and email.
- **Analytics dashboard:** Live headcount, check-in, attendance rate, pending-leave, and payroll-readiness metrics with Chart.js visualization.
- **Demo data seeder:** A deterministic Faker-powered script creates a demo company, admin, configurable employee set, profiles, salary structures, attendance, leave activity, and credentials.

## Stack

FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL (production), SQLite (local development), JWT, Pydantic v2, Jinja2, Chart.js, and pytest. `faker` is included as a development/demo dependency for `seed_demo_data.py`; it is not required by the web service at runtime.

## Database design choices

- `users` has unique indexed email and login ID fields plus a composite company/year/serial constraint for generated employee IDs. Accounts use soft deletion through `is_active`.
- Attendance is constrained to one record per employee and date. Leave allocations are unique per employee and leave type.
- Employee profiles, salary structures, attendance, and leave requests are separate tables keyed to the base `User` identity, keeping salary information behind admin-only endpoints.

## Security

Employees are provisioned by administrators, receive a one-time temporary password, and must change it before app access. Passwords are bcrypt hashed; JWTs contain only identity, role, and expiry. ORM queries are parameterized, `.env` is ignored, and invalid login input such as `' OR 1=1` is rejected.

## Local setup

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

Set `DATABASE_URL` to a PostgreSQL connection string and provide a strong `SECRET_KEY` for production.

### Seed demo data

Run against a database:

```bash
DATABASE_URL="sqlite:///./dayflow.db" python seed_demo_data.py
```

The default creates 25 employees. Set `SEED_EMPLOYEE_COUNT` (3–100) for a different amount. For more than 15 employees, credentials are also written to `seed_credentials.txt`.

To re-seed a database that already contains company data, set `SEED_RESET=true` (or `"1"`):

```bash
SEED_RESET=true python seed_demo_data.py
```

> **Warning:** Setting `SEED_RESET=true` permanently deletes all existing company data, users, profiles, attendance records, leave requests, and salary structures before re-seeding.


### Demo credentials

- **Admin:** `alex.rao@dayflowdemo.com` / `AdminPass123!`
- **Employee credentials:** Individual employee temporary passwords are printed by `seed_demo_data.py` at seed time (and saved to `seed_credentials.txt` for seeded runs over 15 employees). They are not reproducible after the fact, so if a fresh seed run is performed, employee credentials must be recorded from that run's output.

## Deployment

The live service is deployed on Render: https://dayflow-hrms-jq5c.onrender.com

`render.yaml` installs dependencies, runs `alembic upgrade head`, and starts Uvicorn. Configure `DATABASE_URL` with the Render PostgreSQL connection string and `SECRET_KEY` in Render environment variables.

## Verification

```bash
pytest -q
```

## Known Limitations

- Only profile pictures can be uploaded. The app does not provide a general document repository for resumes, certificates, or identity proofs.
- Credentials and workflow notifications are not delivered by email; employees see relevant state only within the app.
- Payroll is an on-demand preview rather than an immutable payroll-run system; it does not generate payslips or cover statutory rules for every jurisdiction.