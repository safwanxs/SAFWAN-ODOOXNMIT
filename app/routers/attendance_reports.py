from calendar import monthrange
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_password_changed, require_role
from app.database import get_db
from app.models.attendance import Attendance
from app.models.leave_request import LeaveRequest
from app.models.user import User
from app.schemas.attendance import AttendanceDayResponse, AttendanceDayRow, AttendanceMonthResponse, AttendanceMonthSummary

router = APIRouter(prefix="/attendance", tags=["attendance reporting"])
STANDARD_WORKDAY_HOURS = 8.0
HALF_DAY_HOURS = 4.0


def worked_hours(check_in: datetime | None, check_out: datetime | None) -> float:
    if check_in is None or check_out is None:
        return 0.0
    return round(max(0.0, (check_out - check_in).total_seconds() / 3600), 2)


def row_for(user: User, selected_date: date, record: Attendance | None, on_leave: bool = False) -> AttendanceDayRow:
    hours = worked_hours(record.check_in_time, record.check_out_time) if record else 0.0
    status = "Leave" if on_leave else "Absent" if record is None else "Half-day" if record.check_out_time is not None and hours < HALF_DAY_HOURS else "Present"
    return AttendanceDayRow(
        user_id=user.id,
        employee_name=f"{user.first_name} {user.last_name}",
        date=selected_date,
        status=status,
        check_in_time=record.check_in_time if record else None,
        check_out_time=record.check_out_time if record else None,
        work_hours=hours,
        extra_hours=round(max(0.0, hours - STANDARD_WORKDAY_HOURS), 2),
    )


@router.get("", response_model=AttendanceDayResponse)
def admin_day_attendance(
    attendance_date: date = Query(default_factory=date.today, alias="date"),
    display_mode: str = Query(default="date", pattern="^(date|day)$"),
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    employees = db.scalars(select(User).where(User.company_id == admin.company_id, User.is_active.is_(True)).order_by(User.first_name, User.last_name)).all()
    records = db.scalars(select(Attendance).where(Attendance.date == attendance_date, Attendance.user_id.in_([employee.id for employee in employees]))).all() if employees else []
    approved_leave_users = set(db.scalars(select(LeaveRequest.user_id).where(LeaveRequest.status == "approved", LeaveRequest.start_date <= attendance_date, LeaveRequest.end_date >= attendance_date, LeaveRequest.user_id.in_([employee.id for employee in employees]))).all()) if employees else set()
    by_user = {record.user_id: record for record in records}
    return AttendanceDayResponse(date=attendance_date, display_mode=display_mode, attendance=[row_for(employee, attendance_date, by_user.get(employee.id), employee.id in approved_leave_users) for employee in employees])


@router.get("/me", response_model=AttendanceMonthResponse)
def my_month_attendance(
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    year: int = Query(default_factory=lambda: date.today().year, ge=1900, le=2100),
    current_user: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
):
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    records = db.scalars(select(Attendance).where(Attendance.user_id == current_user.id, Attendance.date >= first_day, Attendance.date <= last_day).order_by(Attendance.date)).all()
    leaves = db.scalars(select(LeaveRequest).where(LeaveRequest.user_id == current_user.id, LeaveRequest.status == "approved", LeaveRequest.start_date <= last_day, LeaveRequest.end_date >= first_day)).all()
    leave_days = set()
    for leave in leaves:
        day = max(first_day, leave.start_date)
        last_leave_day = min(last_day, leave.end_date)
        while day <= last_leave_day:
            leave_days.add(day)
            day = day.fromordinal(day.toordinal() + 1)
    by_date = {record.date: record for record in records}
    rows = [row_for(current_user, day, by_date.get(day), day in leave_days) for day in sorted(set(by_date) | leave_days)]
    today = date.today()
    effective_end = min(last_day, today) if first_day <= today else last_day
    working_days = sum(1 for day_number in range(1, effective_end.day + 1) if date(year, month, day_number).weekday() < 5) if first_day <= today else 0
    present = sum(1 for row in rows if row.status in {"Present", "Half-day"})
    return AttendanceMonthResponse(
        summary=AttendanceMonthSummary(month=month, year=year, days_present=present, leaves_count=len(leave_days), total_working_days=working_days),
        attendance=rows,
    )
