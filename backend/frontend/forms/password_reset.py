
import logging

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from utilities.commons.basic_validators import (
    is_valid_email,
    is_valid_username,
)

logger = logging.getLogger(__name__)

UserModel = get_user_model()


class CustomResetPasswordForm(forms.Form):

    """
    Password reset request form that accepts either:
      - a valid email address, OR
      - a valid alphanumeric username.
    """

    identifier = forms.CharField(
        label=_("Email or Username"),
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add bootstrap class to all fields
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " form-control").strip()

    def clean_identifier(self):
        value = (self.cleaned_data.get("identifier") or "").strip()

        if not value:
            raise forms.ValidationError(
                _("Please enter your email address or username.")
            )

        # Decide what the user intended: email vs username
        if "@" in value:
            # Treat as email
            if not is_valid_email(value):
                raise forms.ValidationError(
                    _("Please enter a valid email address.")
                )
            self.cleaned_data["identifier_type"] = "email"
        else:
            # Treat as username
            if not is_valid_username(value):
                raise forms.ValidationError(
                    _(
                        "Please enter a valid username. "
                        "Username can only contain letters and numbers."
                    )
                )
            self.cleaned_data["identifier_type"] = "username"

        return value

    def get_user(self):
        """
        Resolve the user based on the cleaned identifier + identifier_type.

        Returns:
            User instance or None

        """
        identifier = (self.cleaned_data.get("identifier") or "").strip()
        identifier_type = self.cleaned_data.get("identifier_type")

        if not identifier or not identifier_type:
            return None

        qs = UserModel.objects.filter(is_active=True)

        # If your auth model has deleted_at, respect it; otherwise ignore.
        try:
            UserModel._meta.get_field("deleted_at")
            qs = qs.filter(deleted_at__isnull=True)
        except Exception:
            pass

        if identifier_type == "email":
            user = qs.filter(email__iexact=identifier).first()
        else:  # username
            user = qs.filter(username__iexact=identifier).first()

        logger.info(
            f"CustomResetPasswordForm.get_user: identifier={identifier}, "
            f"type={identifier_type}, found={bool(user)}"
        )
        return user


class CustomResetPasswordKeyForm(forms.Form):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput,
        label="New password",
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm new password",
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        logger.info(
            "CustomResetPasswordKeyForm initialized: user=%s",
            getattr(user, "pk", None),
        )

        if not self.user:
            logger.error("No user provided during form initialization")

    def clean(self):
        cleaned_data = super().clean()

        if not self.user:
            raise forms.ValidationError(
                "Invalid or expired password reset token."
            )

        p1 = cleaned_data.get("new_password1")
        p2 = cleaned_data.get("new_password2")

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")

        validate_password(p1, self.user)

        return cleaned_data

    def save(self):
        if not self.user:
            raise ValueError("Cannot save password without user")

        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        self.user.save(update_fields=["password"])

        logger.info("Password reset successful for user pk=%s", self.user.pk)

        return self.user

