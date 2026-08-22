from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.id_generator import generate_login_id
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.company import Company
from app.models.user import User, UserRole
from app.schemas.company import CompanySignup
from app.schemas.user import ChangePasswordRequest, LoginRequest, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: CompanySignup, db: Session = Depends(get_db)):
    if db.scalar(select(Company.id).limit(1)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company onboarding has already been completed")
    code = payload.company_code.upper()
    company = Company(name=payload.company_name, company_code=code)
    year = datetime.now(timezone.utc).year
    admin = User(
        login_id=generate_login_id(code, payload.admin_first_name, payload.admin_last_name, year, 0),
        first_name=payload.admin_first_name,
        last_name=payload.admin_last_name,
        email=str(payload.admin_email).lower(),
        phone=payload.admin_phone,
        hashed_password=hash_password(payload.password),
        role=UserRole.ADMIN,
        must_change_password=False,
        year_of_joining=year,
        serial_number=0,
        company=company,
    )
    db.add_all([company, admin])
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company code or email already exists")
    db.refresh(admin)
    return admin


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()
    user = db.scalar(select(User).where(or_(User.login_id == identifier.upper(), User.email == identifier.lower())))
    # A single response avoids leaking whether an account exists or its account state.
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return Token(access_token=create_access_token(user.id, user.role.value), must_change_password=user.must_change_password)


@router.post("/change-password", response_model=UserResponse)
def change_password(payload: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.must_change_password = False
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
