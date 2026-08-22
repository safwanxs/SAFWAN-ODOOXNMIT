from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.core.id_generator import generate_login_id, generate_temp_password, next_serial_number
from app.core.security import hash_password
from app.database import get_db
from app.models.company import Company
from app.models.user import User, UserRole
from app.schemas.user import EmployeeCreate, EmployeeCreated, UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/employees", response_model=EmployeeCreated, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(User.email == str(payload.email).lower())) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    company = db.get(Company, admin.company_id)
    serial = next_serial_number(db, company.id, payload.year_of_joining)
    temp_password = generate_temp_password()
    employee = User(
        login_id=generate_login_id(company.company_code, payload.first_name, payload.last_name, payload.year_of_joining, serial),
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=str(payload.email).lower(),
        phone=payload.phone,
        hashed_password=hash_password(temp_password),
        role=UserRole.EMPLOYEE,
        must_change_password=True,
        email_verified=True,
        year_of_joining=payload.year_of_joining,
        serial_number=serial,
        company_id=company.id,
    )
    db.add(employee)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to provision employee")
    db.refresh(employee)
    return EmployeeCreated(**UserResponse.model_validate(employee, from_attributes=True).model_dump(), temporary_password=temp_password)


@router.get("/hr-requests", response_model=list[UserResponse])
def list_hr_requests(admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    users = db.scalars(
        select(User).where(
            User.company_id == admin.company_id,
            User.hr_approval_status == "pending",
        )
    ).all()
    return users


@router.post("/hr-requests/{user_id}/approve", response_model=UserResponse)
def approve_hr_request(user_id: int, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.company_id == admin.company_id,
            User.hr_approval_status == "pending",
        )
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HR request not found")

    user.hr_approval_status = "approved"
    # Approved HR receives elevated admin-level access as the application role model does not have a separate HR enum tier
    user.role = UserRole.ADMIN
    db.commit()
    db.refresh(user)
    return user


@router.post("/hr-requests/{user_id}/reject", response_model=UserResponse)
def reject_hr_request(user_id: int, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.company_id == admin.company_id,
            User.hr_approval_status == "pending",
        )
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HR request not found")

    user.hr_approval_status = "rejected"
    user.role = UserRole.EMPLOYEE
    db.commit()
    db.refresh(user)
    return user

