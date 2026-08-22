from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.attendance import Attendance

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
