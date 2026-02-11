import logging
from datetime import timedelta

from django import forms
from django.utils import timezone
from helpdesk.models import *

from users.models import Employee, SignUpRequest

logger = logging.getLogger(__name__)

class SignUpRequestForm(forms.ModelForm):

    """
    Admin form for SignUpRequest.

    - ADD:
        * expires_at auto-set to now + 24h
        * shown as read-only / disabled
        * user dropdown shows only NOT VERIFIED employees
        * extra employee fields hidden
    - EDIT:
        * expires_at editable (must be in the future)
        * user dropdown shows only NOT VERIFIED employees + current user
        * extra employee fields (email, first_name, last_name, username) shown read-only
    """

    user = forms.ModelChoiceField(
        queryset=Employee.objects.none(),  # real queryset set in __init__
        widget=forms.Select(attrs={"class": "select2"}),
        help_text="Employee requesting signup",
    )

    # Extra, read-only info copied from Employee (on edit)
    email = forms.EmailField(label="Email", required=False)
    first_name = forms.CharField(label="First name", required=False)
    last_name = forms.CharField(label="Last name", required=False)
    username = forms.CharField(label="Username", required=False)

    class Meta:
        model = SignUpRequest
        fields = [
            "user",
            "email", "first_name", "last_name", "username",
            "sso_provider", "sso_id",
            "expires_at",
        ]
        widgets = {
            "sso_provider": forms.Select(attrs={"class": "select2"}),
        }

    def __init__(self, *args, **kwargs):
        self._user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["expires_at"].required = False

        is_add = self.instance.pk is None

        # ------------------------------
        # User queryset: only NOT VERIFIED employees
        # ------------------------------
        base_qs = Employee.objects.filter(
            is_active=True,
            deleted_at__isnull=True,
            is_verified=False,
        )

        if not is_add and getattr(self.instance, "user_id", None):
            # On edit: make sure current user is still selectable
            current_user_qs = Employee.all_objects.filter(pk=self.instance.user_id)
            self.fields["user"].queryset = base_qs | current_user_qs
        else:
            # On add: only not-verified employees
            self.fields["user"].queryset = base_qs

        # ------------------------------
        # Extra employee fields: hide on ADD, readonly on EDIT
        # ------------------------------
        if is_add:
            # ADD: hide these fields completely
            from django.forms import HiddenInput
            for name in ["email", "first_name", "last_name", "username"]:
                self.fields[name].widget = HiddenInput()
                self.fields[name].required = False
        else:
            # EDIT: show as read-only / disabled
            for name in ["email", "first_name", "last_name", "username"]:
                self.fields[name].widget.attrs["readonly"] = True
                self.fields[name].disabled = True

        # ------------------------------
        # expires_at: auto-set + readonly on ADD
        # ------------------------------
        if is_add:
            default_expires = timezone.now() + timedelta(hours=24)
            self.initial["expires_at"] = default_expires

            field = self.fields["expires_at"]
            from django.forms import SplitDateTimeWidget

            if isinstance(field.widget, SplitDateTimeWidget):
                for w in field.widget.widgets:
                    w.attrs["readonly"] = True
                    w.attrs["disabled"] = True
            else:
                field.widget.attrs["readonly"] = True
                field.widget.attrs["disabled"] = True

        # Populate employee info only on edit
        if not is_add:
            self._populate_employee_fields()

        logger.debug(
            "Initialized SignUpRequestForm (instance=%s, user=%s)",
            getattr(self.instance, "pk", None),
            self._user,
        )

    # ------------------------------
    # Populate readonly employee fields (EDIT)
    # ------------------------------
    def _populate_employee_fields(self):
        employee = None

        if getattr(self.instance, "user_id", None):
            employee = self.instance.user
        elif "user" in self.data and self.data.get("user"):
            try:
                employee = Employee.all_objects.get(pk=self.data.get("user"))
            except (Employee.DoesNotExist, ValueError, TypeError):
                employee = None

        if not employee:
            return

        self.fields["email"].initial = employee.email
        self.fields["first_name"].initial = employee.first_name
        self.fields["last_name"].initial = employee.last_name
        self.fields["username"].initial = employee.username

    # ------------------------------
    # Per-user limit validation
    # ------------------------------
    def clean_user(self):
        user = self.cleaned_data.get("user")
        if not user:
            return user

        qs = SignUpRequest.objects.filter(user=user, deleted_at__isnull=True)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        existing_count = qs.count()
        from django.conf import settings
        max_limit = getattr(settings, 'SIGNUP_REQUEST_MAX_PER_USER', '2')
        if existing_count >= max_limit:
            raise forms.ValidationError(
                f"Maximum {max_limit} signup requests are allowed for this user."
            )

        return user

    # ------------------------------
    # expires_at validation
    # ------------------------------
    def clean_expires_at(self):
        """
        On EDIT, ensure expires_at is in the future.
        On ADD, value is overridden in save().
        """
        expires_at = self.cleaned_data.get("expires_at")

        if self.instance.pk and expires_at:
            now = timezone.now()
            if expires_at <= now:
                raise forms.ValidationError("Expiry time must be in the future.")

        return expires_at

    # ------------------------------
    # Save logic (no email here, admin handles that)
    # ------------------------------
    def save(self, commit=True, user=None):
        """
        - On create: force expires_at = now + 24h.
        - On update: keep existing expires_at (validated by clean_expires_at).
        Email sending is handled in SignUpRequestAdmin.save_model.
        """
        effective_user = user or self._user
        is_new = self.instance.pk is None

        instance = super().save(commit=False)

        if is_new:
            instance.expires_at = timezone.now() + timedelta(hours=24)
            logger.info(
                "Auto-set expires_at for new SignUpRequest: %s",
                instance.expires_at,
            )

        if commit:
            if effective_user:
                instance.save(user=effective_user)
            else:
                instance.save()
            self.save_m2m()

        return instance
