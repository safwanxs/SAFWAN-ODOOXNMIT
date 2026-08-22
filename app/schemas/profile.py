from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


class ProfileUpdate(BaseModel):
    phone: str | None = Field(default=None, max_length=32)
    about: str | None = None
    interests: str | None = None
    skills: str | None = None
    certifications: str | None = None
    date_of_birth: date | None = None
    address: str | None = None
    nationality: str | None = None
    personal_email: EmailStr | None = None
    gender: str | None = None
    marital_status: str | None = None
    date_of_joining: date | None = None
    bank_account_number: str | None = None
    bank_name: str | None = None
    ifsc: str | None = None
    pan: str | None = None
    uan: str | None = None
    profile_picture_url: str | None = Field(default=None, max_length=500)


class ProfileResponse(BaseModel):
    user_id: int
    phone: str | None
    about: str | None
    interests: str | None
    skills: str | None
    certifications: str | None
    date_of_birth: date | None
    address: str | None
    nationality: str | None
    personal_email: EmailStr | None
    gender: str | None
    marital_status: str | None
    date_of_joining: date | None
    bank_account_number: str | None
    bank_name: str | None
    ifsc: str | None
    pan: str | None
    uan: str | None
    profile_picture_url: str | None


class SalaryComponent(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["percent", "fixed"]
    value: Decimal = Field(gt=0)


class SalaryUpdate(BaseModel):
    wage_type: Literal["monthly", "yearly"]
    total_wage: Decimal = Field(gt=0)
    components: list[SalaryComponent] = Field(default_factory=list)
    pf_employee_percent: Decimal = Field(default=Decimal("12"), ge=0, le=100)
    pf_employer_percent: Decimal = Field(default=Decimal("12"), ge=0, le=100)
    professional_tax: Decimal = Field(default=Decimal("0"), ge=0)

    @model_validator(mode="after")
    def components_fit_total_wage(self):
        used = sum((item.value if item.kind == "fixed" else self.total_wage * item.value / 100 for item in self.components), Decimal("0"))
        if used > self.total_wage:
            raise ValueError("Salary components cannot exceed total wage")
        return self


class SalaryResponse(SalaryUpdate):
    user_id: int


class AttendanceResponse(BaseModel):
    id: int
    user_id: int
    date: date
    check_in_time: datetime
    check_out_time: datetime | None

    model_config = {"from_attributes": True}
