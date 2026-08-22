from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class LeaveType(str, Enum):
    PAID_TIME_OFF = "paid_time_off"
    SICK_LEAVE = "sick_leave"
    UNPAID_LEAVE = "unpaid_leave"


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveRequestCreate(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date: date
    remarks: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def valid_date_range(self):
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        return self


class LeaveReview(BaseModel):
    status: LeaveStatus
    admin_comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def final_status_only(self):
        if self.status not in {LeaveStatus.APPROVED, LeaveStatus.REJECTED}:
            raise ValueError("Leave review status must be approved or rejected")
        return self


class LeaveRequestResponse(BaseModel):
    id: int
    user_id: int
    employee_name: str | None = None
    leave_type: LeaveType
    start_date: date
    end_date: date
    days_requested: int
    remarks: str | None
    status: LeaveStatus
    attachment_url: str | None
    admin_comment: str | None
    reviewed_by: int | None
    reviewed_at: datetime | None


class LeaveAllocationResponse(BaseModel):
    leave_type: LeaveType
    days_available: int


class PublicHolidayResponse(BaseModel):
    name: str
    date: date


class LeaveCalendarResponse(BaseModel):
    year: int
    requests: list[LeaveRequestResponse]
    public_holidays: list[PublicHolidayResponse]
