from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.attendance import Attendance
from app.models.leave_request import LeaveRequest
from app.models.salary_structure import SalaryStructure
from app.models.user import User, UserRole
from app.schemas.payroll import DashboardResponse

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)) -> DashboardResponse:
    today = date.today()
    employees = db.scalars(select(User).where(User.company_id == admin.company_id, User.role == UserRole.EMPLOYEE, User.is_active.is_(True))).all()
    employee_ids = [employee.id for employee in employees]
    checked_in = 0 if not employee_ids else db.scalar(select(func.count()).select_from(Attendance).where(Attendance.user_id.in_(employee_ids), Attendance.date == today, Attendance.check_out_time.is_(None))) or 0
    pending = db.scalar(select(func.count()).select_from(LeaveRequest).join(User, User.id == LeaveRequest.user_id).where(User.company_id == admin.company_id, LeaveRequest.status == "pending")) or 0
    payroll_ready = 0 if not employee_ids else db.scalar(select(func.count()).select_from(SalaryStructure).where(SalaryStructure.user_id.in_(employee_ids))) or 0
    headcount = len(employees)
    return DashboardResponse(headcount=headcount, checked_in_today=checked_in, attendance_rate=round(checked_in / headcount * 100, 2) if headcount else 0, pending_leave_requests=pending, payroll_ready_count=payroll_ready, month=today.month, year=today.year)