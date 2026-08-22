from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    about: Mapped[str | None] = mapped_column(Text)
    interests: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[str | None] = mapped_column(Text)
    certifications: Mapped[str | None] = mapped_column(Text)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(Text)
    nationality: Mapped[str | None] = mapped_column(String(100))
    personal_email: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(50))
    marital_status: Mapped[str | None] = mapped_column(String(50))
    date_of_joining: Mapped[date | None] = mapped_column(Date)
    bank_account_number: Mapped[str | None] = mapped_column(String(100))
    bank_name: Mapped[str | None] = mapped_column(String(150))
    ifsc: Mapped[str | None] = mapped_column(String(32))
    pan: Mapped[str | None] = mapped_column(String(32))
    uan: Mapped[str | None] = mapped_column(String(32))
    profile_picture_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
