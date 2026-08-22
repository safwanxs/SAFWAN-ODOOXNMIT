from datetime import date, datetime

from pydantic import BaseModel, Field


class AttendanceDayRow(BaseModel):
    user_id: int
    employee_name: str
    date: date
    status: str
    check_in_time: datetime | None
    check_out_time: datetime | None
    work_hours: float
    extra_hours: float


class AttendanceMonthSummary(BaseModel):
    month: int
    year: int
    days_present: int
    leaves_count: int
    total_working_days: int


class AttendanceMonthResponse(BaseModel):
    summary: AttendanceMonthSummary
    attendance: list[AttendanceDayRow]


class AttendanceDayResponse(BaseModel):
    date: date
    display_mode: str
    attendance: list[AttendanceDayRow]
