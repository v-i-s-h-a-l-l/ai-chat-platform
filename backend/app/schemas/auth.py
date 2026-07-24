from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.password_validation import validate_password_strength


class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    message: str
