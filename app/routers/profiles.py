from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_password_changed, require_role
from app.database import get_db
from app.models.employee_profile import EmployeeProfile
from app.models.salary_structure import SalaryStructure
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate, SalaryResponse, SalaryUpdate

router = APIRouter(prefix="/api/profiles", tags=["profiles"])
PUBLIC_FIELDS = {"about", "interests", "skills", "certifications", "profile_picture_url"}
SELF_EDITABLE_FIELDS = {"phone", "address", "profile_picture_url"}


def get_profile(db: Session, user_id: int) -> EmployeeProfile:
    profile = db.scalar(select(EmployeeProfile).where(EmployeeProfile.user_id == user_id))
    if profile is None:
        profile = EmployeeProfile(user_id=user_id)
        db.add(profile)
        db.flush()
    return profile


def profile_response(profile: EmployeeProfile, user: User, can_view_private: bool) -> ProfileResponse:
    values = {field: getattr(profile, field) for field in ProfileResponse.model_fields if field not in {"user_id", "phone"}}
    if not can_view_private:
        values = {field: (value if field in PUBLIC_FIELDS else None) for field, value in values.items()}
        phone = None
    else:
        phone = user.phone
    return ProfileResponse(user_id=user.id, phone=phone, **values)


def target_user(db: Session, current_user: User, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or user.company_id != current_user.company_id or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return user


@router.get("/me", response_model=ProfileResponse)
def my_profile(current_user: User = Depends(require_password_changed), db: Session = Depends(get_db)):
    return profile_response(get_profile(db, current_user.id), current_user, True)


@router.get("/{user_id}", response_model=ProfileResponse)
def read_profile(user_id: int, current_user: User = Depends(require_password_changed), db: Session = Depends(get_db)):
    user = target_user(db, current_user, user_id)
    return profile_response(get_profile(db, user.id), user, current_user.id == user.id or current_user.role.value == "admin")


@router.put("/{user_id}", response_model=ProfileResponse)
def update_profile(user_id: int, payload: ProfileUpdate, current_user: User = Depends(require_password_changed), db: Session = Depends(get_db)):
    user = target_user(db, current_user, user_id)
    changes = payload.model_dump(exclude_unset=True)
    is_admin = current_user.role.value == "admin"
    if not is_admin:
        if current_user.id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only edit your own profile")
        restricted = set(changes) - SELF_EDITABLE_FIELDS
        if restricted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only edit address, phone, and profile picture")
    profile = get_profile(db, user.id)
    for field, value in changes.items():
        if field == "phone":
            user.phone = value
        else:
            setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile_response(profile, user, True)


@router.get("/{user_id}/salary", response_model=SalaryResponse)
def read_salary(user_id: int, _: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    salary = db.scalar(select(SalaryStructure).where(SalaryStructure.user_id == user_id))
    if salary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salary structure not found")
    return SalaryResponse(user_id=salary.user_id, wage_type=salary.wage_type, total_wage=salary.total_wage, components=salary.components, pf_employee_percent=salary.pf_employee_percent, pf_employer_percent=salary.pf_employer_percent, professional_tax=salary.professional_tax)


@router.put("/{user_id}/salary", response_model=SalaryResponse)
def update_salary(user_id: int, payload: SalaryUpdate, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    user = target_user(db, admin, user_id)
    salary = db.scalar(select(SalaryStructure).where(SalaryStructure.user_id == user.id))
    if salary is None:
        salary = SalaryStructure(user_id=user.id, wage_type=payload.wage_type, total_wage=payload.total_wage, components=[])
        db.add(salary)
    salary.wage_type = payload.wage_type
    salary.total_wage = payload.total_wage
    salary.components = [item.model_dump(mode="json") for item in payload.components]
    salary.pf_employee_percent = payload.pf_employee_percent
    salary.pf_employer_percent = payload.pf_employer_percent
    salary.professional_tax = payload.professional_tax
    db.commit()
    db.refresh(salary)
    return SalaryResponse(user_id=salary.user_id, wage_type=salary.wage_type, total_wage=salary.total_wage, components=salary.components, pf_employee_percent=salary.pf_employee_percent, pf_employer_percent=salary.pf_employer_percent, professional_tax=salary.professional_tax)
