"""
⚠️ USERS APP — SCHEMA FROZEN ⚠️

This app owns IDENTITY ONLY.

DO NOT add:
- HR models
- Team / Department models
- Support / Bug models
- Business-domain relations

See releases/users-django-app.md for details.
"""

from .employee import Employee
from .password_reset_request import PasswordResetRequest
from .signup_request import SignUpRequest

__all__ = [
    "Employee",
    "PasswordResetRequest",
    "SignUpRequest",
    ]
