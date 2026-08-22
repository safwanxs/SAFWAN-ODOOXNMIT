import csv
import io
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.leave_request import LeaveRequest
from app.models.public_holiday import PublicHoliday
from app.models.salary_structure import SalaryStructure
from app.models.user import User
from app.schemas.payroll import PayrollComponentResponse, PayrollPreviewResponse

MONEY = Decimal("0.01")
ZERO = Decimal("0")
PAID_LEAVE_TYPES = {"paid_time_off", "sick_leave"}


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def month_dates(year: int, month: int) -> list[date]:
    return [date(year, month, day) for day in range(1, monthrange(year, month)[1] + 1)]


def build_payroll_preview(db: Session, user: User, month: int, year: int) -> PayrollPreviewResponse:
    salary = db.scalar(select(SalaryStructure).where(SalaryStructure.user_id == user.id))
    if salary is None:
        raise ValueError("Salary structure not found")

    dates = month_dates(year, month)
    start_date, end_date = dates[0], dates[-1]
    holiday_dates = set(db.scalars(select(PublicHoliday.date).where(PublicHoliday.company_id == user.company_id, PublicHoliday.date >= start_date, PublicHoliday.date <= end_date)).all())
    workdays = [day for day in dates if day.weekday() < 5 and day not in holiday_dates]
    attendance_dates = set(db.scalars(select(Attendance.date).where(Attendance.user_id == user.id, Attendance.date >= start_date, Attendance.date <= end_date)).all())
    leaves = db.scalars(select(LeaveRequest).where(LeaveRequest.user_id == user.id, LeaveRequest.status == "approved", LeaveRequest.start_date <= end_date, LeaveRequest.end_date >= start_date)).all()
    leave_by_day: dict[date, str] = {}
    for leave in leaves:
        for day in workdays:
            if leave.start_date <= day <= leave.end_date:
                leave_by_day[day] = leave.leave_type

    unpaid_days = sum(1 for day in workdays if leave_by_day.get(day) == "unpaid_leave")
    paid_leave_days = sum(1 for day in workdays if leave_by_day.get(day) in PAID_LEAVE_TYPES)
    present_days = sum(1 for day in workdays if day in attendance_dates and day not in leave_by_day)
    missing_days = sum(1 for day in workdays if day not in attendance_dates and day not in leave_by_day)
    total_working_days = len(workdays)
    payable_days = total_working_days - unpaid_days - missing_days

    defined_wage = Decimal(salary.total_wage)
    monthly_wage = defined_wage if salary.wage_type == "monthly" else defined_wage / Decimal("12")
    ratio = Decimal(payable_days) / Decimal(total_working_days) if total_working_days else ZERO
    components: list[PayrollComponentResponse] = []
    for item in salary.components:
        value = Decimal(str(item["value"]))
        monthly_amount = monthly_wage * value / Decimal("100") if item["kind"] == "percent" else value
        components.append(PayrollComponentResponse(name=item["name"], kind=item["kind"], value=value, monthly_amount=money(monthly_amount), payable_amount=money(monthly_amount * ratio)))

    gross_pay = money(monthly_wage * ratio)
    basic_amount = next((component.payable_amount for component in components if component.name.lower() == "basic"), gross_pay)
    employee_pf = money(basic_amount * Decimal(salary.pf_employee_percent) / Decimal("100"))
    employer_pf = money(basic_amount * Decimal(salary.pf_employer_percent) / Decimal("100"))
    professional_tax = money(Decimal(salary.professional_tax) * ratio)
    deductions = money(employee_pf + professional_tax)
    return PayrollPreviewResponse(
        user_id=user.id, employee_name=f"{user.first_name} {user.last_name}", month=month, year=year,
        total_working_days=total_working_days, present_days=present_days, paid_leave_days=paid_leave_days,
        unpaid_leave_days=unpaid_days, missing_attendance_days=missing_days, payable_days=payable_days,
        monthly_wage=money(monthly_wage), gross_pay=gross_pay, components=components,
        provident_fund_employee=employee_pf, provident_fund_employer=employer_pf,
        professional_tax=professional_tax, total_deductions=deductions, net_pay=money(gross_pay - deductions),
    )


def build_company_payroll_csv(db: Session, company_id: int, month: int, year: int) -> str:
    users = db.scalars(
        select(User).where(User.company_id == company_id, User.is_active == True).order_by(User.id)
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Employee ID", "Employee Name", "Work Email", "Month", "Year",
        "Total Working Days", "Present Days", "Paid Leave Days", "Unpaid Leave Days",
        "Missing Days", "Payable Days", "Monthly Wage", "Gross Pay",
        "Employee PF", "Employer PF", "Professional Tax", "Total Deductions", "Net Pay"
    ])

    for user in users:
        try:
            preview = build_payroll_preview(db, user, month, year)
            writer.writerow([
                user.login_id,
                f"{user.first_name} {user.last_name}",
                user.email,
                month,
                year,
                preview.total_working_days,
                preview.present_days,
                preview.paid_leave_days,
                preview.unpaid_leave_days,
                preview.missing_attendance_days,
                preview.payable_days,
                str(preview.monthly_wage),
                str(preview.gross_pay),
                str(preview.provident_fund_employee),
                str(preview.provident_fund_employer),
                str(preview.professional_tax),
                str(preview.total_deductions),
                str(preview.net_pay),
            ])
        except ValueError:
            # User does not have salary structure configured
            continue

    return output.getvalue()