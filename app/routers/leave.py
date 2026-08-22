from datetime import datetime, timezone
from pathlib import Path
import secrets

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_password_changed, require_role
from app.database import get_db
from app.models.leave_allocation import LeaveAllocation
from app.models.leave_request import LeaveRequest
from app.models.public_holiday import PublicHoliday
from app.models.user import User
from app.schemas.leave import LeaveAllocationResponse, LeaveCalendarResponse, LeaveRequestCreate, LeaveRequestResponse, LeaveReview, LeaveStatus, LeaveType, PublicHolidayResponse

router = APIRouter(prefix="/leave", tags=["leave"])
DEFAULT_ALLOCATIONS = {LeaveType.PAID_TIME_OFF.value: 24, LeaveType.SICK_LEAVE.value: 7, LeaveType.UNPAID_LEAVE.value: 365}
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads"


def ensure_allocations(db: Session, user_id: int) -> list[LeaveAllocation]:
    allocations = db.scalars(select(LeaveAllocation).where(LeaveAllocation.user_id == user_id)).all()
    by_type = {allocation.leave_type: allocation for allocation in allocations}
    for leave_type, days in DEFAULT_ALLOCATIONS.items():
        if leave_type not in by_type:
            allocation = LeaveAllocation(user_id=user_id, leave_type=leave_type, days_available=days)
            db.add(allocation)
            allocations.append(allocation)
    db.flush()
    return allocations


def leave_response(request: LeaveRequest, employee_name: str | None = None) -> LeaveRequestResponse:
    return LeaveRequestResponse(
        id=request.id, user_id=request.user_id, employee_name=employee_name, leave_type=request.leave_type,
        start_date=request.start_date, end_date=request.end_date, days_requested=request.days_requested,
        remarks=request.remarks, status=request.status, attachment_url=request.attachment_url,
        admin_comment=request.admin_comment, reviewed_by=request.reviewed_by, reviewed_at=request.reviewed_at,
    )


@router.get("/allocations/me", response_model=list[LeaveAllocationResponse])
def my_allocations(current_user: User = Depends(require_password_changed), db: Session = Depends(get_db)):
    allocations = ensure_allocations(db, current_user.id)
    db.commit()
    return [LeaveAllocationResponse(leave_type=item.leave_type, days_available=item.days_available) for item in sorted(allocations, key=lambda item: item.leave_type)]


@router.post("/requests", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
def request_leave(payload: LeaveRequestCreate, current_user: User = Depends(require_password_changed), db: Session = Depends(get_db)):
    days_requested = (payload.end_date - payload.start_date).days + 1
    allocations = {item.leave_type: item for item in ensure_allocations(db, current_user.id)}
    allocation = allocations[payload.leave_type.value]
    if days_requested > allocation.days_available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Requested {days_requested} days exceeds {allocation.days_available} days available")
    request = LeaveRequest(user_id=current_user.id, leave_type=payload.leave_type.value, start_date=payload.start_date, end_date=payload.end_date, days_requested=days_requested, remarks=payload.remarks, status=LeaveStatus.PENDING.value)
    db.add(request)
    db.commit()
    db.refresh(request)
    return leave_response(request)


@router.get("/requests/me", response_model=list[LeaveRequestResponse])
def my_requests(current_user: User = Depends(require_password_changed), db: Session = Depends(get_db)):
    requests = db.scalars(select(LeaveRequest).where(LeaveRequest.user_id == current_user.id).order_by(LeaveRequest.start_date.desc())).all()
    return [leave_response(request) for request in requests]


@router.get("/requests", response_model=list[LeaveRequestResponse])
def all_requests(admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.execute(select(LeaveRequest, User).join(User, User.id == LeaveRequest.user_id).where(User.company_id == admin.company_id).order_by(LeaveRequest.created_at.desc())).all()
    return [leave_response(request, f"{user.first_name} {user.last_name}") for request, user in rows]


@router.patch("/requests/{request_id}", response_model=LeaveRequestResponse)
def review_request(request_id: int, payload: LeaveReview, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    request = db.get(LeaveRequest, request_id)
    employee = db.get(User, request.user_id) if request else None
    if request is None or employee is None or employee.company_id != admin.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")
    if request.status != LeaveStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending leave requests can be reviewed")
    if payload.status == LeaveStatus.APPROVED:
        allocations = {item.leave_type: item for item in ensure_allocations(db, employee.id)}
        allocation = allocations[request.leave_type]
        if request.days_requested > allocation.days_available:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient remaining leave allocation")
        allocation.days_available -= request.days_requested
    request.status = payload.status.value
    request.admin_comment = payload.admin_comment
    request.reviewed_by = admin.id
    request.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return leave_response(request, f"{employee.first_name} {employee.last_name}")


@router.post("/requests/{request_id}/attachment", response_model=LeaveRequestResponse)
def upload_sick_certificate(request_id: int, attachment: UploadFile = File(...), current_user: User = Depends(require_password_changed), db: Session = Depends(get_db)):
    request = db.get(LeaveRequest, request_id)
    if request is None or request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")
    if request.leave_type != LeaveType.SICK_LEAVE.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attachments are only accepted for sick leave")
    suffix = Path(attachment.filename or "certificate").suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Certificate must be a PDF or image")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_urlsafe(16)}{suffix}"
    destination = UPLOAD_DIR / filename
    with destination.open("wb") as output:
        while chunk := attachment.file.read(1024 * 1024):
            output.write(chunk)
    request.attachment_url = f"/static/uploads/{filename}"
    db.commit()
    db.refresh(request)
    return leave_response(request)


@router.get("/calendar/me", response_model=LeaveCalendarResponse)
def my_leave_calendar(year: int, current_user: User = Depends(require_password_changed), db: Session = Depends(get_db)):
    requests = db.scalars(select(LeaveRequest).where(LeaveRequest.user_id == current_user.id, LeaveRequest.start_date <= datetime(year, 12, 31).date(), LeaveRequest.end_date >= datetime(year, 1, 1).date()).order_by(LeaveRequest.start_date)).all()
    holidays = db.scalars(select(PublicHoliday).where(PublicHoliday.company_id == current_user.company_id, PublicHoliday.date >= datetime(year, 1, 1).date(), PublicHoliday.date <= datetime(year, 12, 31).date()).order_by(PublicHoliday.date)).all()
    return LeaveCalendarResponse(year=year, requests=[leave_response(request) for request in requests], public_holidays=[PublicHolidayResponse(name=holiday.name, date=holiday.date) for holiday in holidays])
