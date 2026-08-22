from pydantic import BaseModel

from app.models.user import UserRole


class EmployeeCard(BaseModel):
    id: int
    first_name: str
    last_name: str
    role: UserRole
    profile_picture_url: str | None = None
    status: str

