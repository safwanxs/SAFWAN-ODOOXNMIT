from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.dependencies import require_password_changed
from app.database import get_db
from app.models.attendance import Attendance
from app.models.employee_profile import EmployeeProfile
from app.models.leave_request import LeaveRequest
from app.models.user import User
from app.schemas.employee import EmployeeCard

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeCard])
def list_employees(
    search: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(require_password_changed),
    db: Session = Depends(get_db),
):
    today = date.today()
    query = select(User, EmployeeProfile.profile_picture_url).outerjoin(EmployeeProfile, EmployeeProfile.user_id == User.id).where(User.company_id == current_user.company_id, User.is_active.is_(True))
    if search:
        term = f"%{search.lower()}%"
        query = query.where(or_(func.lower(User.first_name).like(term), func.lower(User.last_name).like(term), func.lower(User.login_id).like(term)))
    users = db.execute(query.order_by(User.first_name, User.last_name)).all()
    checked_in = set(db.scalars(select(Attendance.user_id).where(Attendance.date == today, Attendance.check_out_time.is_(None))).all())
    on_leave = set(db.scalars(select(LeaveRequest.user_id).where(LeaveRequest.status == "approved", LeaveRequest.start_date <= today, LeaveRequest.end_date >= today)).all())
    return [EmployeeCard(id=user.id, first_name=user.first_name, last_name=user.last_name, role=user.role, profile_picture_url=picture, status=("on_leave" if user.id in on_leave else "checked_in" if user.id in checked_in else "absent")) for user, picture in users]
