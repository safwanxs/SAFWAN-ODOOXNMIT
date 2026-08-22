from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    wage_type: Mapped[str] = mapped_column(String(16), nullable=False)
    total_wage: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    components: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    pf_employee_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("12"))
    pf_employer_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("12"))
    professional_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
