import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.id_generator import generate_login_id, next_serial_number
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.company import Company
from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User, UserRole
from app.schemas.company import CompanySignup
from app.schemas.user import ChangePasswordRequest, EmployeeSelfRegister, LoginRequest, Token, UserResponse
from app.services.email import send_verification_email

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
        email_verified=True,
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


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: EmployeeSelfRegister, db: Session = Depends(get_db)):
    company = db.scalar(select(Company).limit(1))
    if company is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company has not been set up yet.")

    existing_email = db.scalar(select(User.id).where(User.email == str(payload.email).lower()))
    if existing_email is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    year = datetime.now(timezone.utc).year
    serial = next_serial_number(db, company.id, year)
    login_id = generate_login_id(company.company_code, payload.first_name, payload.last_name, year, serial)

    user = User(
        login_id=login_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=str(payload.email).lower(),
        hashed_password=hash_password(payload.password),
        role=UserRole.EMPLOYEE,
        must_change_password=False,
        email_verified=False,
        hr_approval_status="pending" if payload.role == "hr" else None,
        year_of_joining=year,
        serial_number=serial,
        company_id=company.id,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    verification_token = EmailVerificationToken(
        user_id=user.id,
        token=token_str,
        expires_at=expires_at,
    )
    db.add(verification_token)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    send_verification_email(user.email, user.first_name, token_str)

    return {"message": "Registered. Check your email (or server logs) to verify your account before logging in."}


@router.get("/verify-email")
def verify_email(token: str = Query(min_length=1), db: Session = Depends(get_db)):
    token_row = db.scalar(select(EmailVerificationToken).where(EmailVerificationToken.token == token))
    now = datetime.now(timezone.utc)
    if token_row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification link")

    exp = token_row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if exp < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification link")

    user = db.get(User, token_row.user_id)
    if user:
        user.email_verified = True
    db.delete(token_row)
    db.commit()
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()
    user = db.scalar(select(User).where(or_(User.login_id == identifier.upper(), User.email == identifier.lower())))
    # A single response avoids leaking whether an account exists or its account state.
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email before logging in.")
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
