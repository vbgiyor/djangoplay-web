# paystream/app_settings/links.py
"""
Central link expiry configuration.

Put fixed, project-level defaults here (days).
Used by email templates, signup/reset code and allauth.
"""

# How many days verification links are valid
EMAIL_VERIFICATION_EXPIRE_DAYS = 7

# How many days password reset links are valid (2 days is typical)
PASSWORD_RESET_EXPIRE_DAYS = 2

# How many days unsubscribe links (if short-lived) are valid
UNSUBSCRIBE_EXPIRE_DAYS = 30

# Convenience dict for callers
LINK_EXPIRY_DAYS = {
    "email_verification": EMAIL_VERIFICATION_EXPIRE_DAYS,
    "password_reset": PASSWORD_RESET_EXPIRE_DAYS,
    "unsubscribe": UNSUBSCRIBE_EXPIRE_DAYS,
}
