from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

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
        assert client.get("/employees", headers=auth_header(token)).status_code == 403
        assert client.get("/auth/me", headers=auth_header(token)).json()["email"] == employee["email"]
        changed = client.post("/auth/change-password", headers=auth_header(token), json={
            "current_password": employee["temporary_password"], "new_password": "NewPass1", "confirm_new_password": "NewPass1",
        })
        assert changed.status_code == 200
        assert changed.json()["must_change_password"] is False
        assert client.post("/auth/login", json={"identifier": employee["login_id"], "password": "NewPass1"}).json()["must_change_password"] is False
        assert client.get("/auth/me").status_code == 401
