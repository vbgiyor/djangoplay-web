import logging
from datetime import date, datetime, timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from users.models import *
from users.services.member import MemberService
from utilities.utils.locations.phone_number_validations import validate_phone_number

logger = logging.getLogger(__name__)

class MemberStatusForm(forms.ModelForm):

    """Form for MemberStatus model with validation."""

    class Meta:
        model = MemberStatus
        fields = ['code', 'name', 'is_active']
        widgets = {
            'code': forms.TextInput(),
            'name': forms.TextInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        code = cleaned_data.get('code')
        name = cleaned_data.get('name')

        if code and MemberStatus.objects.filter(
            code__iexact=code, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            logger.warning(f"Duplicate status code: {code}")
            raise ValidationError({'code': 'Status code already exists.'})

        if name and MemberStatus.objects.filter(
            name__iexact=name, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            logger.warning(f"Duplicate status name: {name}")
            raise ValidationError({'name': 'Status name already exists.'})

        return cleaned_data

class MemberForm(forms.ModelForm):

    """Form for Member model with validation."""

    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True, deleted_at__isnull=True),
        required=True,
        help_text="Associated Employee for authentication"
    )

    class Meta:
        model = Member
        fields = [
            'email', 'first_name', 'last_name', 'phone_number',
            'address', 'status', 'is_active', 'employee'
        ]
        widgets = {
            'status': forms.Select(),
            'address': forms.Select(),
            'employee': forms.Select(),
        }
        labels = {
            'members': 'SSO Users',
        }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone_number = cleaned_data.get('phone_number')
        employee = cleaned_data.get('employee')

        if email and MemberService.is_duplicate_email(email, exclude_pk=self.instance.pk):
            logger.warning(f"Duplicate email detected: {email}")
            raise ValidationError({'email': 'Email already exists.'})

        if phone_number and not validate_phone_number(phone_number):
            logger.warning(f"Invalid phone number format: {phone_number}")
            raise ValidationError({'phone_number': 'Phone number must be in international format (e.g., +1234567890).'})

        if employee and Member.objects.filter(
            employee=employee, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            logger.warning(f"Employee already linked to another member: {employee.employee_code}")
            raise ValidationError({'employee': 'This employee is already linked to another member.'})

        return cleaned_data

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


class PasswordResetRequestForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True, deleted_at__isnull=True),
        widget=forms.Select(attrs={'class': 'select2'}),
        help_text="Employee requesting password reset"
    )

    class Meta:
        model = PasswordResetRequest
        fields = ['user', 'used']
        labels = {
            'used': 'Token Consumed?',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            # Hide token on ADD form
            self.fields.pop('used', None)  # also hide 'used' on add

    def save(self, commit=True, *args, **kwargs):
        instance = super().save(commit=False)
        if not instance.pk:
            # Only set expires_at on creation
            instance.expires_at = timezone.now() + timedelta(hours=24)
        if commit:
            instance.save()
        return instance


class SupportTicketForm(forms.ModelForm):

    """
    Form for creating/updating SupportTicket instances.

    - Excludes system-managed / audit fields
    - Exposes `resolved_at` as a DATE ONLY field in the UI
    - Converts date → datetime for the model
    - Auto-sets resolved_at = today when status is RESOLVED/CLOSED and no date is provided
    - Passes `user` through to SupportTicket.save(user=...) so audit fields work
    """

    # Explicit field to avoid SplitDateTimeField / "Enter a list of values" issue
    resolved_at = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Resolution date (optional; defaults to today when resolved/closed).",
    )

    class Meta:
        model = SupportTicket
        exclude = (
            "id",
            "ticket_number",
            "emails_sent",
            "client_ip",
            "deleted_at",
            "deleted_by",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "history",
        )
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
            # DO NOT put resolved_at here; we defined it explicitly above
        }

    def __init__(self, *args, **kwargs):
        """
        Optionally accept `user` and store it for use in save():
        form = SupportTicketForm(request.POST, user=request.user)
        """
        self._user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        logger.debug(
            "Initialized SupportTicketForm for instance=%s (user=%s)",
            getattr(self.instance, "pk", None),
            self._user,
        )

        # If there is an existing datetime, prefill only the date part
        if self.instance and self.instance.pk and self.instance.resolved_at:
            if isinstance(self.instance.resolved_at, datetime):
                self.initial["resolved_at"] = self.instance.resolved_at.date()
            else:
                # just in case it's already a date
                self.initial["resolved_at"] = self.instance.resolved_at

    def clean(self):
        logger.debug("SupportTicketForm.clean() called")
        cleaned_data = super().clean()

        if self.errors:
            logger.warning(
                "SupportTicketForm validation errors for instance=%s: %s",
                getattr(self.instance, "pk", None),
                self.errors.as_json(),
            )
        else:
            logger.info(
                "SupportTicketForm validated successfully for instance=%s",
                getattr(self.instance, "pk", None),
            )

        return cleaned_data

    def save(self, commit=True, user=None):
        """
        Save the SupportTicket instance.

        - Uses `user` argument if provided, otherwise falls back to `self._user`.
        - Converts date field to datetime for the model.
        - If status is RESOLVED/CLOSED and no date is provided — set to today.
        """
        effective_user = user or self._user

        logger.info(
            "SupportTicketForm.save() called for instance=%s (commit=%s, user=%s)",
            getattr(self.instance, "pk", None),
            commit,
            effective_user,
        )

        # Build instance without hitting DB yet
        instance = super().save(commit=False)

        # Get the date value from the form
        resolved_date = self.cleaned_data.get("resolved_at")

        if isinstance(resolved_date, datetime):
            # Somehow already a datetime — just use it
            instance.resolved_at = resolved_date
        elif isinstance(resolved_date, date):
            # Convert date → datetime at midnight
            instance.resolved_at = timezone.make_aware(
                datetime.combine(resolved_date, datetime.min.time())
            )
        else:
            # No date provided: auto-set when status is resolved/closed
            if instance.status in (SupportStatus.RESOLVED, SupportStatus.CLOSED):
                today = timezone.localdate()
                instance.resolved_at = timezone.make_aware(
                    datetime.combine(today, datetime.min.time())
                )
            else:
                # keep unresolved if not resolved/closed
                instance.resolved_at = None

        if commit:
            logger.debug(
                "Calling SupportTicket.save(user=...) for instance=%s",
                getattr(instance, "pk", None),
            )
            instance.save(user=effective_user)
            self.save_m2m()
            logger.info(
                "SupportTicket instance saved (pk=%s, ticket_number=%s)",
                instance.pk,
                instance.ticket_number,
            )
        else:
            logger.debug(
                "SupportTicketForm.save() called with commit=False; instance not saved to DB"
            )

        return instance
