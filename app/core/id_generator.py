import secrets
import string

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


def generate_login_id(company_code: str, first_name: str, last_name: str, year_of_joining: int, serial_number: int) -> str:
    return f"{company_code.upper()}{first_name[:2].upper()}{last_name[:2].upper()}{year_of_joining}{serial_number:04d}"


def next_serial_number(db: Session, company_id: int, year: int) -> int:
    highest = db.scalar(select(func.max(User.serial_number)).where(User.company_id == company_id, User.year_of_joining == year))
    return (highest or 0) + 1


def generate_temp_password(length: int = 12) -> str:
    if length < 8:
        raise ValueError("Temporary passwords must be at least 8 characters")
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    required = [secrets.choice(string.ascii_uppercase), secrets.choice(string.ascii_lowercase), secrets.choice(string.digits), secrets.choice("!@#$%^&*")]
    return "".join(required + [secrets.choice(alphabet) for _ in range(length - len(required))])

