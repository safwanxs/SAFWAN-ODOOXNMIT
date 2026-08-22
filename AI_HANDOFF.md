# Dayflow HRMS — AI Handoff

Last updated: 2026-08-22  
Repository: https://github.com/safwanxs/SAFWAN-ODOOXNMIT  
Live app: https://dayflow-hrms-jq5c.onrender.com  
Branch: `main`

## Current State

Dayflow is a FastAPI HRMS demo with all planned phases complete:

- Auth: company onboarding, admin-provisioned employees, generated login IDs, JWT sessions, forced password change.
- Employees/profiles: directory, role-aware access, salary privacy, profile-picture upload.
- Attendance: check in/out, admin daily reporting, employee monthly reporting, calculated hours.
- Leave: allocations, requests, sick-certificate upload, approval/rejection, approved-leave attendance status.
- Payroll: attendance/leave-linked payable-day calculation, salary components, PF, professional tax, employee/admin preview.
- Analytics: Chart.js dashboard for headcount, check-ins, pending leave, payroll readiness.

## Essential Files

- `app/main.py` — app setup, router registration, page routes, static mount.
- `app/core/security.py` and `app/core/dependencies.py` — auth primitives; avoid changing without an isolated bug fix.
- `app/models/` — SQLAlchemy models.
- `app/routers/` — APIs.
- `app/templates/base.html` — shared navigation; uses `localStorage.token` and `/auth/me` to show logout state.
- `app/static/css/dayflow.css` — shared dark UI styles.
- `seed_demo_data.py` — fresh-database Faker demo seeder.
- `render.yaml` — Render build/start configuration.
- `tests/test_auth.py` — current full test suite.

## Main Pages

`/`, `/login`, `/change-password`, `/employees`, `/profile/{user_id}`, `/attendance/view`, `/time-off`, `/payroll`, `/dashboard`.

## Important APIs

- Auth: `/auth/signup`, `/auth/login`, `/auth/change-password`, `/auth/me`
- Provisioning: `POST /admin/employees`
- Profiles: `GET/PUT /api/profiles/{user_id}`; `POST /api/profiles/{user_id}/picture`
- Attendance: `/api/attendance/check-in`, `/api/attendance/check-out`, `/attendance`, `/attendance/me`
- Leave: `/leave/allocations/me`, `/leave/requests`, `/leave/requests/me`, `PATCH /leave/requests/{id}`
- Payroll: `/api/payroll/me`, `/api/payroll/{user_id}`, `GET /api/payroll/export` (admin-only)
- Dashboard: `/api/dashboard` (admin-only)

## Authorization Rules

- Employees are admin-provisioned; no employee public signup.
- Temp-password users must change their password before protected app routes.
- Employees can only edit limited fields on their own profile; admins can edit same-company profiles.
- Salary data, dashboard, and payroll for another employee are admin-only.
- Leave data is private to an employee unless viewed by an admin in the same company.
- Profile pictures may be uploaded by the owner or an admin; JPEG/PNG/WebP, max 2 MB.

## Demo Data / Credentials

`seed_demo_data.py` only runs against a database with no `Company`; it intentionally refuses to reseed an existing DB.

```bash
SEED_EMPLOYEE_COUNT=25 python seed_demo_data.py
```

Allowed employee count: 3–100. For more than 15 employees, the script writes local credentials to `seed_credentials.txt`, which is gitignored. Do not commit or publish credential files/passwords.

Local SQLite and Render PostgreSQL are separate databases. Seed Render through its service shell with `python seed_demo_data.py` before using generated demo credentials there. If the Render DB already has a company, use its existing admin or reset it only with explicit approval.

## Deployment

Render uses `render.yaml`:

- Build: `pip install -r requirements.txt && alembic upgrade head`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Required env: `DATABASE_URL`, `SECRET_KEY`

Pushing `main` triggers the Render deployment.

## Verification

Last known state: **21 tests pass**.

```bash
python -m pytest -q
```


Tests cover auth, role rules, profiles, attendance, leave, payroll, analytics, injection-style login input, profile-picture upload, and payroll CSV export.

## Recent Commits

- `166940b docs: update live demo and shipped features`
- `a917b1b feat: expand demo data seeder with faker`
- `997b4a0 feat: add profile picture upload`
- `4832d36 feat: reflect logged-in state in nav bar`
- `85430f7 fix: show readable validation errors instead of object output`
- `e6c67de feat: add shared dark frontend layout`
- `a9225ae feat: add attendance-linked payroll and analytics`
- `5089567 feat: complete leave and time-off management`

## Known Limitations

- No general document repository: profile pictures and sick-leave certificates only.
- No email delivery for credentials or notifications.
- Payroll is an on-demand preview, not immutable payroll runs/payslips or comprehensive statutory compliance.
- README has no live screenshots yet; capture real seeded Render screenshots before adding them.


## Future-AI Working Rules

- Preserve API contracts unless explicitly asked to change them.
- Do not casually alter models, migrations, `security.py`, `dependencies.py`, or `id_generator.py`.
- Run relevant tests before edits and the full suite afterward.
- Keep commits focused; push `main` only after validation.

## Suggested Next Steps

1. Seed the Render database, then verify the documented demo login there.
2. Capture real screenshots from the seeded Render app and add them under `docs/screenshots/`.
3. Implement CSV export only if requested, then document it accurately.
4. Record the demo video from the seeded live deployment.
