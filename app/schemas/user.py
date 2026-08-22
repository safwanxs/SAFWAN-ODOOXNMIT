from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.user import UserRole


class EmployeeCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=32)
    year_of_joining: int = Field(ge=1900, le=2100)
    role: UserRole = UserRole.EMPLOYEE

    @model_validator(mode="after")
    def employee_role_only(self):
        if self.role != UserRole.EMPLOYEE:
            raise ValueError("Only employee accounts may be provisioned by this endpoint")
        return self


class UserResponse(BaseModel):
    id: int
    login_id: str
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole
    must_change_password: bool
    email_verified: bool = False
    hr_approval_status: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}



class EmployeeCreated(UserResponse):
    temporary_password: str


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
    confirm_new_password: str

    @model_validator(mode="after")
    def validate_new_password(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match")
        if not any(char.isupper() for char in self.new_password) or not any(char.isdigit() for char in self.new_password):
            raise ValueError("New password must contain an uppercase letter and a digit")
        return self


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool


class EmployeeSelfRegister(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str
    role: str

    @model_validator(mode="after")
    def validate_registration(self):
        if self.role not in ("employee", "hr"):
            raise ValueError("Role must be 'employee' or 'hr'")
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not any(char.isupper() for char in self.password) or not any(char.isdigit() for char in self.password):
            raise ValueError("Password must contain an uppercase letter and a digit")
        return self


