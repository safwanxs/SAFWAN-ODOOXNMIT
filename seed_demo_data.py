"""Dayflow HRMS demo data seeder.

Run once after ``alembic upgrade head``. The script refuses to seed a database
that already contains a company, so it never silently mixes demo data with
existing data.
"""

import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from random import Random

from faker import Faker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine, SessionLocal  # noqa: E402
from app.core.id_generator import generate_login_id, generate_temp_password  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.attendance import Attendance  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.employee_profile import EmployeeProfile  # noqa: E402
from app.models.leave_allocation import LeaveAllocation  # noqa: E402
from app.models.leave_request import LeaveRequest  # noqa: E402
from app.models.public_holiday import PublicHoliday  # noqa: E402
from app.models.salary_structure import SalaryStructure  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

ADMIN_PASSWORD = "AdminPass123!"
COMPANY_CODE = "DF"
YEAR = date.today().year
NUM_EMPLOYEES = int(os.environ.get("SEED_EMPLOYEE_COUNT", "25"))
MAX_EMPLOYEES = 100

# Keep demo data reproducible. Remove these seeds for genuinely random demo data.
Faker.seed(42)
fake = Faker("en_IN")
rng = Random(42)

ROLE_BANDS = {
    "Software Engineer": (55000, 80000),
    "Senior Software Engineer": (70000, 90000),
    "HR Executive": (38000, 55000),
    "Product Designer": (52000, 78000),
    "QA Engineer": (45000, 65000),
    "Sales Associate": (35000, 52000),
    "Marketing Analyst": (42000, 62000),
    "DevOps Engineer": (60000, 85000),
    "Finance Analyst": (48000, 70000),
    "Customer Support Lead": (40000, 58000),
    "Operations Manager": (65000, 90000),
    "Business Analyst": (50000, 72000),
}
LEAVE_STATUSES = ("pending", "approved", "rejected")
LEAVE_TYPES = ("paid_time_off", "sick_leave", "unpaid_leave")


def unique_email(first_name: str, last_name: str, used_emails: set[str]) -> str:
    base = f"{first_name.lower()}.{last_name.lower()}".replace("'", "").replace(" ", "")
    email = f"{base}@dayflowdemo.com"
    suffix = 2
    while email in used_emails:
        email = f"{base}{suffix}@dayflowdemo.com"
        suffix += 1
    used_emails.add(email)
    return email


def leave_dates(today: date, status: str) -> tuple[date, date]:
    if status == "approved":
        start = today - timedelta(days=rng.randint(4, 14))
    else:
        start = today + timedelta(days=rng.randint(2, 25))
    duration = rng.randint(1, 3)
    return start, start + timedelta(days=duration - 1)


if not 3 <= NUM_EMPLOYEES <= MAX_EMPLOYEES:
    raise ValueError(f"SEED_EMPLOYEE_COUNT must be between 3 and {MAX_EMPLOYEES}")

Base.metadata.create_all(bind=engine)
db = SessionLocal()
credentials_log: list[tuple[str, str, str, str]] = []

try:
    if db.query(Company).first():
        print("A Company already exists — refusing to reseed. Wipe the DB first if you want a clean seed.")
        sys.exit(1)

    company = Company(name="Dayflow Demo Co", company_code=COMPANY_CODE, logo_url=None)
    db.add(company)
    db.flush()

    admin = User(
        login_id=generate_login_id(COMPANY_CODE, "Alex", "Rao", YEAR, 1),
        first_name="Alex", last_name="Rao", email="alex.rao@dayflowdemo.com", phone="9990001111",
        hashed_password=hash_password(ADMIN_PASSWORD), role=UserRole.ADMIN, must_change_password=False,
        year_of_joining=YEAR, serial_number=1, company_id=company.id, is_active=True,
    )
    db.add(admin)
    db.flush()
    credentials_log.append(("ADMIN", admin.login_id, admin.email, ADMIN_PASSWORD))

    db.add(PublicHoliday(company_id=company.id, name="Independence Day", date=date(YEAR, 8, 15)))

    employees: list[tuple[User, str, Decimal]] = []
    used_emails = {admin.email}
    designations = tuple(ROLE_BANDS)
    for serial_number in range(2, NUM_EMPLOYEES + 2):
        first_name, last_name = fake.first_name(), fake.last_name()
        designation = rng.choice(designations)
        lower, upper = ROLE_BANDS[designation]
        wage = Decimal(rng.randrange(lower, upper + 1, 1000))
        temp_password = generate_temp_password()
        employee = User(
            login_id=generate_login_id(COMPANY_CODE, first_name, last_name, YEAR, serial_number),
            first_name=first_name, last_name=last_name, email=unique_email(first_name, last_name, used_emails),
            phone=f"999000{serial_number:04d}", hashed_password=hash_password(temp_password),
            role=UserRole.EMPLOYEE, must_change_password=True, year_of_joining=YEAR,
            serial_number=serial_number, company_id=company.id, is_active=True,
        )
        db.add(employee)
        db.flush()
        credentials_log.append(("EMPLOYEE", employee.login_id, employee.email, temp_password))
        employees.append((employee, designation, wage))

        db.add(EmployeeProfile(
            user_id=employee.id, about=f"{designation} at Dayflow Demo Co.",
            skills="Python, SQL, Communication", date_of_birth=fake.date_of_birth(minimum_age=22, maximum_age=55),
            address=f"{fake.city()}, India", nationality="Indian", gender="Prefer not to say",
            marital_status="Single", date_of_joining=date(YEAR, rng.randint(1, 6), rng.randint(1, 20)),
            bank_name="Demo Bank", bank_account_number=f"DEMOBANK{serial_number:06d}",
            ifsc=f"DEMO{serial_number:07d}",
        ))
        db.add(SalaryStructure(
            user_id=employee.id, wage_type="monthly", total_wage=wage,
            components=[
                {"name": "Basic", "kind": "percent", "value": "50"},
                {"name": "HRA", "kind": "percent", "value": "30"},
                {"name": "Allowances", "kind": "percent", "value": "20"},
            ],
            pf_employee_percent=Decimal("12"), pf_employer_percent=Decimal("12"), professional_tax=Decimal("200"),
        ))
        for leave_type, days in (("paid_time_off", 18), ("sick_leave", 10), ("unpaid_leave", 0)):
            db.add(LeaveAllocation(user_id=employee.id, leave_type=leave_type, days_available=days))

    db.flush()

    today = date.today()
    day_cursor = today - timedelta(days=1)
    days_added = 0
    while days_added < 10:
        if day_cursor.weekday() < 5:
            for employee, _designation, _wage in employees:
                check_in = datetime.combine(day_cursor, datetime.min.time()).replace(hour=9, minute=15, tzinfo=timezone.utc)
                db.add(Attendance(user_id=employee.id, date=day_cursor, check_in_time=check_in, check_out_time=check_in.replace(hour=18, minute=5)))
            days_added += 1
        day_cursor -= timedelta(days=1)

    today_checkin = datetime.combine(today, datetime.min.time()).replace(hour=9, minute=5, tzinfo=timezone.utc)
    db.add(Attendance(user_id=employees[0][0].id, date=today, check_in_time=today_checkin, check_out_time=None))

    request_count = max(3, round(NUM_EMPLOYEES * 0.15))
    selected_indices = list(range(NUM_EMPLOYEES))
    rng.shuffle(selected_indices)
    for request_number, employee_index in enumerate(selected_indices[:request_count]):
        status = LEAVE_STATUSES[request_number] if request_number < len(LEAVE_STATUSES) else rng.choice(LEAVE_STATUSES)
        leave_type = rng.choice(LEAVE_TYPES)
        start_date, end_date = leave_dates(today, status)
        reviewed = status != "pending"
        db.add(LeaveRequest(
            user_id=employees[employee_index][0].id, leave_type=leave_type, start_date=start_date, end_date=end_date,
            days_requested=(end_date - start_date).days + 1, remarks=fake.sentence(nb_words=5), status=status,
            admin_comment=("Approved for demo" if status == "approved" else "Not approved for this period") if reviewed else None,
            reviewed_by=admin.id if reviewed else None, reviewed_at=datetime.now(timezone.utc) if reviewed else None,
        ))

    db.commit()

    header = f"{'ROLE':<10}{'LOGIN ID':<20}{'EMAIL':<38}{'PASSWORD'}"
    credential_rows = [header, *(f"{role:<10}{login_id:<20}{email:<38}{password}" for role, login_id, email, password in credentials_log)]
    credentials_output = "\n".join(credential_rows)
    print("\nSeed complete.\n")
    print(credentials_output)
    if NUM_EMPLOYEES > 15:
        credentials_path = Path(__file__).with_name("seed_credentials.txt")
        credentials_path.write_text(credentials_output + "\n", encoding="utf-8")
        print(f"\nFull credentials also written to {credentials_path.name}.")
    print("\nAdmin has must_change_password=False — logs straight in.")
    print("Employees have must_change_password=True — first login forces the change-password screen.")
except Exception:
    db.rollback()
    raise
finally:
    db.close()