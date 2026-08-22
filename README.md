# Dayflow — Human Resource Management System

Repo: https://github.com/safwanxs/SAFWAN-ODOOXNMIT

## Problem Statement

HR teams manage attendance, leave, and payroll across scattered tools with no single source of truth or employee self-service. Dayflow centralizes those workflows.

## Tech Stack

FastAPI, SQLAlchemy 2.0, PostgreSQL, Alembic, JWT, Jinja2, pytest.

## Progress

- [x] Phase 1: Foundation, database design, admin-provisioned authentication, and role-based access.
- [x] Phase 2: Employee directory, profiles, salary access controls, and attendance check-in foundation.

## Key Design Decisions

- Company onboarding is a one-time action that creates the first administrator. Employees cannot self-register: an admin provisions their account and receives its one-time temporary password in the creation response.
- Login IDs use the stored company code, first two letters of each name, year of joining, and a company/year serial (for example, `OIJODO20220001`). The composite company/year/serial constraint prevents collisions.
- There is no email-verification flow. Since all employee accounts are created by an authenticated administrator rather than an untrusted party, this keeps onboarding lean for the initial release.
- Passwords are bcrypt hashes. JWT payloads contain only user ID, role, and expiry. Deactivation is a soft delete using `is_active`.
- Employee profile, salary structure, attendance, and leave-status records are separate tables keyed to `User`. This keeps the authentication identity stable for later phases.
- Salary APIs are admin-only as well as hidden in the interface. Employees can update only their own address, phone, and profile picture; all other profile edits require an admin.
- Attendance has one record per employee per day. An open record renders a green status, an approved leave renders an airplane indicator, and otherwise the employee is shown as absent.

## Setup

```bash
git clone https://github.com/safwanxs/SAFWAN-ODOOXNMIT.git
cd SAFWAN-ODOOXNMIT
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Set `DATABASE_URL` in `.env` to a PostgreSQL connection string before production use. The local default SQLite database makes first-run development simple; PostgreSQL is the supported deployed database.

## Verification

```bash
pytest
```

The test suite uses an isolated in-memory SQLite database and covers signup, ID generation, role enforcement, temporary-password login, mandatory password change, profile edit controls, salary privacy, and attendance toggling.
