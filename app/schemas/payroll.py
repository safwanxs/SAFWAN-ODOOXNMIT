from decimal import Decimal

from pydantic import BaseModel


class PayrollComponentResponse(BaseModel):
    name: str
    kind: str
    value: Decimal
    monthly_amount: Decimal
    payable_amount: Decimal


class PayrollPreviewResponse(BaseModel):
    user_id: int
    employee_name: str
    month: int
    year: int
    total_working_days: int
    present_days: int
    paid_leave_days: int
    unpaid_leave_days: int
    missing_attendance_days: int
    payable_days: int
    monthly_wage: Decimal
    gross_pay: Decimal
    components: list[PayrollComponentResponse]
    provident_fund_employee: Decimal
    provident_fund_employer: Decimal
    professional_tax: Decimal
    total_deductions: Decimal
    net_pay: Decimal


class DashboardResponse(BaseModel):
    headcount: int
    checked_in_today: int
    attendance_rate: float
    pending_leave_requests: int
    payroll_ready_count: int
    month: int
    year: int