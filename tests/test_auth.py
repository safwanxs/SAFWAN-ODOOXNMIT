from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.attendance import Attendance
from app.models.leave_request import LeaveRequest

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def signup(client: TestClient):
    return client.post("/auth/signup", json={
        "company_name": "Odoo Innovation",
        "company_code": "OI",
        "admin_first_name": "Asha",
        "admin_last_name": "Khan",
        "admin_email": "asha@example.com",
        "admin_phone": "1234567890",
        "password": "AdminPass1",
        "confirm_password": "AdminPass1",
    })


def admin_token(client: TestClient) -> str:
    response = client.post("/auth/login", json={"identifier": "asha@example.com", "password": "AdminPass1"})
    return response.json()["access_token"]


def create_employee(client: TestClient, token: str, email: str = "john@example.com"):
    return client.post("/admin/employees", headers=auth_header(token), json={
        "first_name": "John", "last_name": "Doe", "email": email, "phone": "9999999999", "year_of_joining": 2022,
    })


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_signup_creates_company_and_admin():
    with TestClient(app) as client:
        response = signup(client)
    assert response.status_code == 201
    assert response.json()["role"] == "admin"
    assert response.json()["must_change_password"] is False


def test_admin_creates_employee_with_unique_formatted_login_id():
    with TestClient(app) as client:
        signup(client)
        token = admin_token(client)
        first = create_employee(client, token, "john@example.com")
        second = create_employee(client, token, "jane@example.com")
    assert first.status_code == 201
    assert first.json()["login_id"] == "OIJODO20220001"
    assert second.json()["login_id"] == "OIJODO20220002"
    assert first.json()["temporary_password"]


def test_non_admin_is_blocked_from_employee_provisioning():
    with TestClient(app) as client:
        signup(client)
        employee = create_employee(client, admin_token(client)).json()
        token = client.post("/auth/login", json={"identifier": employee["login_id"], "password": employee["temporary_password"]}).json()["access_token"]
        response = create_employee(client, token, "other@example.com")
    assert response.status_code == 403


def test_employee_temp_password_change_and_me():
    with TestClient(app) as client:
        signup(client)
        employee = create_employee(client, admin_token(client)).json()
        login = client.post("/auth/login", json={"identifier": employee["email"], "password": employee["temporary_password"]})
        assert login.status_code == 200
        assert login.json()["must_change_password"] is True
        token = login.json()["access_token"]
        assert client.get("/api/employees", headers=auth_header(token)).status_code == 403
        assert client.get("/auth/me", headers=auth_header(token)).json()["email"] == employee["email"]
        changed = client.post("/auth/change-password", headers=auth_header(token), json={
            "current_password": employee["temporary_password"], "new_password": "NewPass1", "confirm_new_password": "NewPass1",
        })
        assert changed.status_code == 200
        assert changed.json()["must_change_password"] is False
        assert client.post("/auth/login", json={"identifier": employee["login_id"], "password": "NewPass1"}).json()["must_change_password"] is False
        assert client.get("/auth/me").status_code == 401


def activate_employee(client: TestClient, employee: dict) -> str:
    token = client.post("/auth/login", json={"identifier": employee["login_id"], "password": employee["temporary_password"]}).json()["access_token"]
    response = client.post("/auth/change-password", headers=auth_header(token), json={
        "current_password": employee["temporary_password"], "new_password": "EmployeePass1", "confirm_new_password": "EmployeePass1",
    })
    assert response.status_code == 200
    return client.post("/auth/login", json={"identifier": employee["email"], "password": "EmployeePass1"}).json()["access_token"]


def test_employee_can_edit_only_own_limited_profile_fields():
    with TestClient(app) as client:
        signup(client)
        employee = create_employee(client, admin_token(client)).json()
        token = activate_employee(client, employee)
        own = client.put(f"/api/profiles/{employee['id']}", headers=auth_header(token), json={"address": "42 Dayflow Road", "phone": "12345"})
        forbidden = client.put(f"/api/profiles/{employee['id']}", headers=auth_header(token), json={"bank_name": "Private Bank"})
    assert own.status_code == 200
    assert own.json()["address"] == "42 Dayflow Road"
    assert forbidden.status_code == 403


def test_employee_cannot_edit_another_profile_and_admin_can_edit_any_profile():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        first = create_employee(client, admin, "john@example.com").json()
        second = create_employee(client, admin, "jane@example.com").json()
        employee_token = activate_employee(client, first)
        forbidden = client.put(f"/api/profiles/{second['id']}", headers=auth_header(employee_token), json={"address": "No access"})
        allowed = client.put(f"/api/profiles/{second['id']}", headers=auth_header(admin), json={"address": "Admin updated", "bank_name": "Dayflow Bank"})
    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["bank_name"] == "Dayflow Bank"


def test_salary_is_admin_only_and_attendance_toggles_status():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        employee = create_employee(client, admin).json()
        employee_token = activate_employee(client, employee)
        saved_salary = client.put(f"/api/profiles/{employee['id']}/salary", headers=auth_header(admin), json={"wage_type": "monthly", "total_wage": "10000", "components": [{"name": "Basic", "kind": "percent", "value": "50"}]})
        denied_salary = client.get(f"/api/profiles/{employee['id']}/salary", headers=auth_header(employee_token))
        checked_in = client.post("/api/attendance/check-in", headers=auth_header(employee_token))
        cards = client.get("/api/employees", headers=auth_header(employee_token)).json()
        checked_out = client.post("/api/attendance/check-out", headers=auth_header(employee_token))
    assert saved_salary.status_code == 200
    assert denied_salary.status_code == 403
    assert checked_in.status_code == 201
    assert next(card for card in cards if card["id"] == employee["id"])["status"] == "checked_in"
    assert checked_out.status_code == 200
    assert checked_out.json()["check_out_time"] is not None


def test_employee_attendance_is_limited_to_own_month_data_and_hours_are_server_computed():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        employee = create_employee(client, admin, "john@example.com").json()
        other = create_employee(client, admin, "jane@example.com").json()
        employee_token = activate_employee(client, employee)
        other_token = activate_employee(client, other)
        day = date(2026, 3, 5)
        db = TestingSessionLocal()
        db.add_all([
            Attendance(user_id=employee["id"], date=day, check_in_time=datetime(2026, 3, 5, 9, tzinfo=timezone.utc), check_out_time=datetime(2026, 3, 5, 19, 15, tzinfo=timezone.utc)),
            Attendance(user_id=other["id"], date=day, check_in_time=datetime(2026, 3, 5, 10, tzinfo=timezone.utc), check_out_time=datetime(2026, 3, 5, 11, tzinfo=timezone.utc)),
        ])
        db.commit()
        db.close()
        own = client.get("/attendance/me?month=3&year=2026", headers=auth_header(employee_token))
        employee_admin_report = client.get("/attendance?date=2026-03-05", headers=auth_header(employee_token))
    assert own.status_code == 200
    assert len(own.json()["attendance"]) == 1
    assert own.json()["attendance"][0]["user_id"] == employee["id"]
    assert own.json()["attendance"][0]["work_hours"] == 10.25
    assert own.json()["attendance"][0]["extra_hours"] == 2.25
    assert employee_admin_report.status_code == 403


def test_admin_day_attendance_includes_records_and_absences():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        employee = create_employee(client, admin, "john@example.com").json()
        absent_employee = create_employee(client, admin, "jane@example.com").json()
        day = date(2026, 4, 6)
        db = TestingSessionLocal()
        db.add(Attendance(user_id=employee["id"], date=day, check_in_time=datetime(2026, 4, 6, 9, tzinfo=timezone.utc), check_out_time=datetime(2026, 4, 6, 17, tzinfo=timezone.utc)))
        db.commit()
        db.close()
        report = client.get("/attendance?date=2026-04-06&display_mode=day", headers=auth_header(admin))
    assert report.status_code == 200
    rows = {row["user_id"]: row for row in report.json()["attendance"]}
    assert rows[employee["id"]]["status"] == "Present"
    assert rows[employee["id"]]["work_hours"] == 8.0
    assert rows[absent_employee["id"]]["status"] == "Absent"
    assert rows[absent_employee["id"]]["check_in_time"] is None


def test_employee_requests_leave_within_allocation_and_overage_is_rejected():
    with TestClient(app) as client:
        signup(client)
        employee = create_employee(client, admin_token(client)).json()
        token = activate_employee(client, employee)
        allocations = client.get("/leave/allocations/me", headers=auth_header(token))
        request = client.post("/leave/requests", headers=auth_header(token), json={"leave_type": "paid_time_off", "start_date": "2026-06-01", "end_date": "2026-06-03", "remarks": "Family trip"})
        overage = client.post("/leave/requests", headers=auth_header(token), json={"leave_type": "sick_leave", "start_date": "2026-07-01", "end_date": "2026-07-10"})
    assert allocations.status_code == 200
    assert next(item for item in allocations.json() if item["leave_type"] == "paid_time_off")["days_available"] == 24
    assert request.status_code == 201
    assert request.json()["days_requested"] == 3
    assert request.json()["status"] == "pending"
    assert overage.status_code == 400
    assert "exceeds" in overage.json()["detail"]


def test_admin_review_updates_allocation_and_attendance_leave_status():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        employee = create_employee(client, admin).json()
        employee_token = activate_employee(client, employee)
        request = client.post("/leave/requests", headers=auth_header(employee_token), json={"leave_type": "paid_time_off", "start_date": "2026-08-10", "end_date": "2026-08-11"}).json()
        forbidden_review = client.patch(f"/leave/requests/{request['id']}", headers=auth_header(employee_token), json={"status": "approved"})
        reviewed = client.patch(f"/leave/requests/{request['id']}", headers=auth_header(admin), json={"status": "approved", "admin_comment": "Approved"})
        allocations = client.get("/leave/allocations/me", headers=auth_header(employee_token)).json()
        employee_requests = client.get("/leave/requests/me", headers=auth_header(employee_token)).json()
        report = client.get("/attendance?date=2026-08-10", headers=auth_header(admin)).json()
        month = client.get("/attendance/me?month=8&year=2026", headers=auth_header(employee_token)).json()
    assert forbidden_review.status_code == 403
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "approved"
    assert next(item for item in allocations if item["leave_type"] == "paid_time_off")["days_available"] == 22
    assert employee_requests[0]["status"] == "approved"
    assert next(row for row in report["attendance"] if row["user_id"] == employee["id"])["status"] == "Leave"
    assert month["summary"]["leaves_count"] == 2


def test_employee_cannot_see_other_employee_leave_requests():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        first = create_employee(client, admin, "john@example.com").json()
        second = create_employee(client, admin, "jane@example.com").json()
        first_token = activate_employee(client, first)
        second_token = activate_employee(client, second)
        client.post("/leave/requests", headers=auth_header(second_token), json={"leave_type": "sick_leave", "start_date": "2026-09-01", "end_date": "2026-09-01"})
        own = client.get("/leave/requests/me", headers=auth_header(first_token))
        all_requests = client.get("/leave/requests", headers=auth_header(first_token))
    assert own.status_code == 200
    assert own.json() == []
    assert all_requests.status_code == 403


def test_payroll_preview_prorates_wage_from_attendance_and_unpaid_leave():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        employee = create_employee(client, admin).json()
        salary = client.put(f"/api/profiles/{employee['id']}/salary", headers=auth_header(admin), json={
            "wage_type": "monthly", "total_wage": "10000",
            "components": [{"name": "Basic", "kind": "percent", "value": "50"}, {"name": "HRA", "kind": "fixed", "value": "1000"}],
            "pf_employee_percent": "12", "pf_employer_percent": "12", "professional_tax": "200",
        })
        db = TestingSessionLocal()
        db.add_all([
            Attendance(user_id=employee["id"], date=date(2026, 6, 1), check_in_time=datetime(2026, 6, 1, 9, tzinfo=timezone.utc), check_out_time=datetime(2026, 6, 1, 17, tzinfo=timezone.utc)),
            LeaveRequest(user_id=employee["id"], leave_type="sick_leave", start_date=date(2026, 6, 2), end_date=date(2026, 6, 2), days_requested=1, status="approved"),
            LeaveRequest(user_id=employee["id"], leave_type="unpaid_leave", start_date=date(2026, 6, 3), end_date=date(2026, 6, 3), days_requested=1, status="approved"),
        ])
        db.commit()
        db.close()
        preview = client.get(f"/api/payroll/{employee['id']}?month=6&year=2026", headers=auth_header(admin))
    assert salary.status_code == 200
    assert preview.status_code == 200
    data = preview.json()
    assert data["total_working_days"] == 22
    assert data["payable_days"] == 2
    assert data["paid_leave_days"] == 1
    assert data["unpaid_leave_days"] == 1
    assert data["missing_attendance_days"] == 19
    assert data["gross_pay"] == "909.09"
    assert data["total_deductions"] == "72.73"
    assert data["net_pay"] == "836.36"


def test_salary_components_cannot_exceed_wage_and_payroll_is_admin_scoped():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        employee = create_employee(client, admin).json()
        employee_token = activate_employee(client, employee)
        invalid = client.put(f"/api/profiles/{employee['id']}/salary", headers=auth_header(admin), json={
            "wage_type": "monthly", "total_wage": "1000", "components": [{"name": "Basic", "kind": "fixed", "value": "1001"}],
        })
        forbidden = client.get(f"/api/payroll/{employee['id']}?month=6&year=2026", headers=auth_header(employee_token))
    assert invalid.status_code == 422
    assert "cannot exceed" in invalid.text
    assert forbidden.status_code == 403


def test_employee_can_view_own_payroll_preview_but_not_without_salary_structure():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        employee = create_employee(client, admin).json()
        employee_token = activate_employee(client, employee)
        missing = client.get("/api/payroll/me?month=6&year=2026", headers=auth_header(employee_token))
        client.put(f"/api/profiles/{employee['id']}/salary", headers=auth_header(admin), json={"wage_type": "monthly", "total_wage": "12000", "components": []})
        own = client.get("/api/payroll/me?month=6&year=2026", headers=auth_header(employee_token))
    assert missing.status_code == 404
    assert own.status_code == 200
    assert own.json()["user_id"] == employee["id"]


def test_admin_dashboard_aggregates_existing_company_data():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        employee = create_employee(client, admin).json()
        request = client.post("/auth/login", json={"identifier": employee["login_id"], "password": employee["temporary_password"]})
        dashboard = client.get("/api/dashboard", headers=auth_header(admin))
        forbidden = client.get("/api/dashboard", headers=auth_header(request.json()["access_token"]))
    assert dashboard.status_code == 200
    assert dashboard.json()["headcount"] == 1
    assert dashboard.json()["payroll_ready_count"] == 0
    assert forbidden.status_code == 403

def test_login_injection_string_is_rejected():
    with TestClient(app) as client:
        signup(client)
        response = client.post("/auth/login", json={"identifier": "' OR 1=1", "password": "anything"})
    assert response.status_code == 401

def test_profile_picture_upload_allows_owner_and_rejects_bad_types_and_other_employees():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        employee = create_employee(client, admin, "john@example.com").json()
        other = create_employee(client, admin, "jane@example.com").json()
        employee_token = activate_employee(client, employee)
        uploaded = client.post(
            f"/api/profiles/{employee['id']}/picture",
            headers=auth_header(employee_token),
            files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\nimage-data", "image/png")},
        )
        invalid_type = client.post(
            f"/api/profiles/{employee['id']}/picture",
            headers=auth_header(employee_token),
            files={"file": ("notes.txt", b"not an image", "text/plain")},
        )
        forbidden = client.post(
            f"/api/profiles/{other['id']}/picture",
            headers=auth_header(employee_token),
            files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\nimage-data", "image/png")},
        )
        admin_uploaded = client.post(
            f"/api/profiles/{other['id']}/picture",
            headers=auth_header(admin),
            files={"file": ("avatar.webp", b"RIFFwebp-data", "image/webp")},
        )
    assert uploaded.status_code == 200
    assert uploaded.json()["profile_picture_url"].startswith("/static/uploads/profile_pictures/")
    assert invalid_type.status_code == 400
    assert "JPEG, PNG, or WebP" in invalid_type.json()["detail"]
    assert forbidden.status_code == 403
    assert admin_uploaded.status_code == 200


def test_admin_export_payroll_csv_and_employee_forbidden():
    with TestClient(app) as client:
        signup(client)
        admin = admin_token(client)
        employee = create_employee(client, admin).json()
        employee_token = activate_employee(client, employee)
        
        # Configure salary for employee
        client.put(
            f"/api/profiles/{employee['id']}/salary",
            headers=auth_header(admin),
            json={"wage_type": "monthly", "total_wage": "12000", "components": [{"name": "Basic", "kind": "percent", "value": "50"}]}
        )

        # Employee cannot export payroll CSV
        forbidden = client.get("/api/payroll/export?month=6&year=2026", headers=auth_header(employee_token))

        # Admin can export payroll CSV
        export = client.get("/api/payroll/export?month=6&year=2026", headers=auth_header(admin))

    assert forbidden.status_code == 403
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"payroll_2026_06.csv\"" in export.headers["content-disposition"]
    csv_text = export.text
    assert "Employee ID" in csv_text
    assert "Net Pay" in csv_text
    assert employee["email"] in csv_text