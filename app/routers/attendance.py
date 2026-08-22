from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_password_changed
from app.database import get_db
from app.models.attendance import Attendance
from app.models.user import User
from app.schemas.profile import AttendanceResponse

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.post("/check-in", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def check_in(current_user: User = Depends(require_password_changed), db: Session = Depends(get_db)):
    today = date.today()
    existing = db.scalar(select(Attendance).where(Attendance.user_id == current_user.id, Attendance.date == today))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendance has already been recorded today")
    record = Attendance(user_id=current_user.id, date=today, check_in_time=datetime.now(timezone.utc))
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/check-out", response_model=AttendanceResponse)
def check_out(current_user: User = Depends(require_password_changed), db: Session = Depends(get_db)):
    record = db.scalar(select(Attendance).where(Attendance.user_id == current_user.id, Attendance.date == date.today()))
    if record is None or record.check_out_time is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No open check-in found today")
    record.check_out_time = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record
