"""Sign-in, passwords, two-factor authentication and user accounts."""
from typing import Self

from pydantic import BaseModel, Field, model_validator

from ..core.i18n import N_
from .common import Role


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def different(self) -> Self:
        if self.current_password == self.new_password:
            raise ValueError(N_("The new password must be different from the current one"))
        if self.new_password.isdigit() or self.new_password.isalpha():
            raise ValueError(N_("Use both letters and numbers in the new password"))
        return self


class OtpCode(BaseModel):
    code: str = Field(pattern=r"^\s*\d{3}\s?\d{3}\s*$")


class PasswordConfirm(BaseModel):
    password: str


# =====================================================================
# Responses (response_model): what each endpoint returns, shown in /docs
# =====================================================================
class SessionUser(BaseModel):
    user_id: int
    username: str
    role: Role
    employee_id: int | None
    name: str
    initials: str
    department_id: int | None
    department: str
    position: str
    totp_enabled: bool
    mfa_required: bool
    pending_action: str | None = Field(None, description="password_change_required | mfa_setup_required")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: SessionUser


class TwoFactorSetup(BaseModel):
    secret: str = Field(description="Key to enter in the authenticator app")
    uri: str = Field(description="otpauth:// link (for QR codes)")


class UserAccount(BaseModel):
    id: int
    username: str
    role: Role
    employee_id: int | None
    employee: str
    totp_enabled: bool
    must_change_password: bool


class TemporaryPassword(BaseModel):
    username: str
    temporary_password: str


class TwoFactorReset(BaseModel):
    username: str
    totp_enabled: bool
