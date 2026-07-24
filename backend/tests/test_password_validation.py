import pytest
from pydantic import ValidationError

from app.schemas.auth import UserRegister
from app.utils.password_validation import validate_password_strength


def test_validate_password_strength_accepts_valid_password():
    assert validate_password_strength("SecureP@ss1") == "SecureP@ss1"


@pytest.mark.parametrize(
    "password, message",
    [
        ("short1!", "at least 8 characters"),
        ("alllowercase1!", "uppercase"),
        ("NoSpecial1", "special character"),
    ],
)
def test_validate_password_strength_rejects_weak_passwords(password: str, message: str):
    with pytest.raises(ValueError, match=message):
        validate_password_strength(password)


def test_user_register_schema_enforces_password_rules():
    with pytest.raises(ValidationError):
        UserRegister(name="Jane Doe", email="jane@example.com", password="weakpass")
