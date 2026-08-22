from pydantic import BaseModel, EmailStr, Field, model_validator


class CompanySignup(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    company_code: str = Field(min_length=2, max_length=16, pattern=r"^[A-Za-z0-9]+$")
    admin_first_name: str = Field(min_length=1, max_length=100)
    admin_last_name: str = Field(min_length=1, max_length=100)
    admin_email: EmailStr
    admin_phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not any(char.isupper() for char in self.password) or not any(char.isdigit() for char in self.password):
            raise ValueError("Password must contain an uppercase letter and a digit")
        return self

