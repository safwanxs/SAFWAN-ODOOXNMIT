from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_password_changed, require_role
from app.database import get_db
from app.models.user import User
from app.schemas.payroll import PayrollPreviewResponse
from app.services.payroll import build_payroll_preview

router = APIRouter(prefix="/api/payroll", tags=["payroll"])


def preview_or_404(db: Session, user: User, month: int, year: int) -> PayrollPreviewResponse:
    try:
        return build_payroll_preview(db, user, month, year)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/me", response_model=PayrollPreviewResponse)
def my_payroll(
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    current_user: User = Depends(require_password_changed), db: Session = Depends(get_db),
) -> PayrollPreviewResponse:
    return preview_or_404(db, current_user, month, year)


@router.get("/{user_id}", response_model=PayrollPreviewResponse)
def employee_payroll(
    user_id: int, month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    admin: User = Depends(require_role("admin")), db: Session = Depends(get_db),
) -> PayrollPreviewResponse:
    user = db.get(User, user_id)
    if user is None or user.company_id != admin.company_id or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return preview_or_404(db, user, month, year)