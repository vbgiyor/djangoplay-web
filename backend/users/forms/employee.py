import logging

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from users.models import Employee, LeaveApplication, LeaveBalance, LeaveType, Team
from users.services.employee import EmployeeService

logger = logging.getLogger(__name__)


class EmployeeForm(forms.ModelForm):

    """
    Form for creating/updating Employee instances.

    - Excludes system-managed / audit fields
    - Delegates validation to ModelForm + Employee.clean()
    - Passes `user` through to Employee.save(user=...) so audit fields work
    """

    class Meta:
        model = Employee
        # Explicitly exclude fields that are auto/managed by system
        exclude = (
            "id",
            "employee_code",
            "address_display",
            "deleted_at",
            "deleted_by",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "history",
        )
        widgets = {
            "hire_date": forms.DateInput(attrs={"type": "date"}),
            "termination_date": forms.DateInput(attrs={"type": "date"}),
            "probation_end_date": forms.DateInput(attrs={"type": "date"}),
            "contract_end_date": forms.DateInput(attrs={"type": "date"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        """
        Optionally accept `user` and store it for use in save():
        form = EmployeeForm(request.POST, user=request.user)
        """
        self._user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        logger.debug(
            "Initialized EmployeeForm for instance=%s (user=%s)",
            getattr(self.instance, "pk", None),
            self._user,
        )

    def clean(self):
        """
        Hook into form-wide validation.

        - Calls parent clean() which in turn:
          * Validates individual fields
          * Calls Employee.clean() (model-level validation)
        - Logs validation outcome.
        """
        logger.debug("EmployeeForm.clean() called")
        cleaned_data = super().clean()

        if self.errors:
            logger.warning(
                "EmployeeForm validation errors for instance=%s: %s",
                getattr(self.instance, "pk", None),
                self.errors.as_json(),
            )
        else:
            logger.info(
                "EmployeeForm validated successfully for instance=%s",
                getattr(self.instance, "pk", None),
            )

        return cleaned_data

    def save(self, commit=True, user=None):
        """
        Save the Employee instance.

        - Uses `user` argument if provided, otherwise falls back to `self._user`.
        - Ensures Employee.save(user=...) is called so audit fields are set.
        """
        effective_user = user or self._user

        logger.info(
            "EmployeeForm.save() called for instance=%s (commit=%s, user=%s)",
            getattr(self.instance, "pk", None),
            commit,
            effective_user,
        )

        # First let ModelForm construct/update the instance without saving to DB
        instance = super().save(commit=False)

        if commit:
            # Call model.save(user=...) so your custom audit logic runs
            logger.debug(
                "Calling Employee.save(user=...) for instance=%s",
                getattr(instance, "pk", None),
            )
            instance.save(user=effective_user)

            # Handle many-to-many fields after the instance has a PK
            self.save_m2m()
            logger.info(
                "Employee instance saved (pk=%s, employee_code=%s)",
                instance.pk,
                instance.employee_code,
            )
        else:
            logger.debug(
                "EmployeeForm.save() called with commit=False; instance not saved to DB"
            )

        return instance

class TeamForm(forms.ModelForm):

    """Form for Team model with validation."""

    class Meta:
        model = Team
        fields = ['name', 'department', 'leader', 'description', 'is_active']
        widgets = {
            'department': forms.Select(),
            'leader': forms.Select(),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        department = cleaned_data.get('department')
        leader = cleaned_data.get('leader')

        if name and department and Team.objects.filter(
            name__iexact=name, department=department, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            logger.warning(f"Duplicate team name in department: {name}, department={department.code}")
            raise ValidationError({'name': 'Team name already exists in this department.'})

        if leader and department and leader.department != department:
            logger.warning(f"Leader not in department: leader={leader.employee_code}, department={department.code}")
            raise ValidationError({'leader': 'Leader must be in the same department.'})

        return cleaned_data

class LeaveTypeForm(forms.ModelForm):

    """Form for LeaveType model with validation."""

    class Meta:
        model = LeaveType
        fields = ['code', 'name', 'default_balance', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        code = cleaned_data.get('code')
        name = cleaned_data.get('name')
        default_balance = cleaned_data.get('default_balance')

        if code and LeaveType.objects.filter(
            code__iexact=code, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            logger.warning(f"Duplicate leave type code: {code}")
            raise ValidationError({'code': 'Leave type code already exists.'})

        if name and LeaveType.objects.filter(
            name__iexact=name, deleted_at__isnull=True
        ).exclude(pk=self.instance.pk).exists():
            logger.warning(f"Duplicate leave type name: {name}")
            raise ValidationError({'name': 'Leave type name already exists.'})

        if default_balance and default_balance < 0:
            logger.warning(f"Negative default balance: {default_balance}")
            raise ValidationError({'default_balance': 'Default balance cannot be negative.'})

        return cleaned_data

class LeaveBalanceForm(forms.ModelForm):

    """Form for LeaveBalance model with validation."""

    class Meta:
        model = LeaveBalance
        fields = ['employee', 'leave_type', 'year', 'balance', 'used', 'reset_date']
        widgets = {
            'employee': forms.Select(),
            'leave_type': forms.Select(),
            'reset_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee')
        leave_type = cleaned_data.get('leave_type')
        year = cleaned_data.get('year')
        balance = cleaned_data.get('balance')
        used = cleaned_data.get('used')
        reset_date = cleaned_data.get('reset_date')

        if employee and leave_type and year and EmployeeService.is_duplicate_balance(
            employee, leave_type, year, exclude_pk=self.instance.pk
        ):
            logger.warning(f"Duplicate leave balance: employee={employee.employee_code}, leave_type={leave_type.code}, year={year}")
            raise ValidationError('Leave balance for this employee, leave type, and year already exists.')

        if balance and used and balance < used:
            logger.warning(f"Used exceeds balance: balance={balance}, used={used}")
            raise ValidationError({'balance': 'Used leave cannot exceed balance.'})

        if year and year > timezone.now().year + 1:
            logger.warning(f"Year too far in future: {year}")
            raise ValidationError({'year': 'Year cannot be more than one year in the future.'})

        if reset_date and year and reset_date.year != year:
            logger.warning(f"Reset date year mismatch: reset_date={reset_date}, year={year}")
            raise ValidationError({'reset_date': 'Reset date must be in the same year.'})

        return cleaned_data

class LeaveApplicationForm(forms.ModelForm):

    """Form for LeaveApplication model with validation."""

    class Meta:
        model = LeaveApplication
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'hours', 'reason', 'status', 'approver']
        widgets = {
            'employee': forms.Select(),
            'leave_type': forms.Select(),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 4}),
            'status': forms.Select(),
            'approver': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.now().date()
        self.fields['approver'].queryset = Employee.objects.filter(
            employment_status__code='ACTV',
            hire_date__isnull=False,
            hire_date__lte=today,
            termination_date__isnull=True
        ) | Employee.objects.filter(
            employment_status__code='ACTV',
            hire_date__isnull=False,
            hire_date__lte=today,
            termination_date__gt=today
        )

    def clean_approver(self):
        approver = self.cleaned_data.get('approver')
        if approver and not approver.is_active_employee:
            raise forms.ValidationError(
                f"Selected approver ({approver.employee_code}) is not an active employee. "
                "Ensure the employee has an active status, a valid hire date, and no past termination date."
            )
        return approver

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee')
        leave_type = cleaned_data.get('leave_type')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        hours = cleaned_data.get('hours')
        approver = cleaned_data.get('approver')

        if start_date and end_date and start_date > end_date:
            logger.warning(f"Invalid date range: start_date={start_date}, end_date={end_date}")
            raise ValidationError({'end_date': 'End date must be after start date.'})

        if hours and hours <= 0:
            logger.warning(f"Non-positive hours: {hours}")
            raise ValidationError({'hours': 'Hours must be positive.'})

        if hours and end_date:
            logger.warning(f"Both hours and end_date specified: hours={hours}, end_date={end_date}")
            raise ValidationError({'hours': 'Cannot specify both hours and end date.'})

        if approver and not approver.is_active_employee:
            logger.warning(f"Invalid approver: {approver.employee_code}")
            raise ValidationError({'approver': 'Approver must be an active employee.'})

        if employee and leave_type and start_date:
            if not EmployeeService.has_sufficient_balance(employee, leave_type, start_date, end_date or start_date):
                logger.warning(f"Insufficient leave balance: employee={employee.employee_code}, leave_type={leave_type.code}")
                raise ValidationError('Insufficient leave balance.')

        return cleaned_data
