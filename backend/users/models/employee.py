import logging
import uuid
from decimal import Decimal

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords
from teamcentral.models import Department, EmployeeType, EmploymentStatus, Role

logger = logging.getLogger(__name__)

class EmployeeManager(BaseUserManager):

    """Manager for Employee model with custom creation logic."""

    def _generate_employee_code(self):
        """Generate unique employee code (DJP + 12 hex chars)."""
        max_attempts = 10
        for attempt in range(max_attempts):
            code_suffix = str(uuid.uuid4()).replace('-', '')[:12].upper()
            employee_code = f"DJP{code_suffix}"
            if not self.model.all_objects.filter(employee_code=employee_code).exists():
                logger.info(f"Generated unique employee_code: {employee_code}")
                return employee_code
            logger.warning(f"Employee code collision: {employee_code}, attempt {attempt + 1}")
        logger.error("Failed to generate unique employee code.")
        raise ValueError("Unable to generate unique employee code.")

    def create_user(self, username, email, password=None, address=None, created_by=None, **extra_fields):
        """Create a regular employee."""
        with transaction.atomic():            
            if not username:
                raise ValueError("Username is required.")
            if not email:
                raise ValueError("Email is required.")
            if created_by and not isinstance(created_by, type(None) | get_user_model()):
                raise ValueError("created_by must be an Employee or None.")
            email = self.normalize_email(email)
            extra_fields['employee_code'] = self._generate_employee_code()
            extra_fields.setdefault('is_staff', False)
            extra_fields.setdefault('is_superuser', False)
            extra_fields.setdefault('is_verified', False)
            extra_fields.setdefault('sso_provider', 'EMAIL')

            user = self.model(
                username=username,
                email=email,
                address=address,
                created_by=created_by,
                **extra_fields
            )
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()    
            user.save(using=self._db)
            return user

    def create_superuser(self, username, email, password=None, address=None, created_by=None, **extra_fields):
        """Create a superuser employee."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role_id', Role.all_objects.get(code='DJGO').id)
        extra_fields.setdefault('approval_limit', Decimal('99999999.99'))
        extra_fields.setdefault('employment_status_id', EmploymentStatus.all_objects.get(code='ACTV').id)
        extra_fields.setdefault('employee_type_id', EmployeeType.all_objects.get(code='FT').id)
        extra_fields.setdefault('hire_date', timezone.now().date())        
        extra_fields.setdefault('department_id', Department.all_objects.get(code='FIN').id)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(username, email, password, address, created_by, **extra_fields)

class Employee(TimeStampedModel, AuditFieldsModel, AbstractUser):

    """Model for employees with comprehensive HR fields."""

    objects = EmployeeManager()
    active_objects = ActiveManager()
    all_objects = models.Manager()


    id = models.AutoField(primary_key=True)
    employee_code = models.CharField(
        max_length=15,
        unique=True,
        validators=[RegexValidator(r'^DJP[A-F0-9]{12}$', message='Employee Code must be DJP + 12 hex chars')],
        help_text='Unique Employee Code (DJP + 12 hex chars)',
        editable=False
    )

    department = models.ForeignKey('teamcentral.Department', on_delete=models.PROTECT, related_name='employees')
    role = models.ForeignKey('teamcentral.Role', on_delete=models.PROTECT, related_name='employees')
    team = models.ForeignKey('teamcentral.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    address = models.ForeignKey('teamcentral.Address', on_delete=models.PROTECT, null=True, blank=True, related_name='employees')
    employment_status = models.ForeignKey('teamcentral.EmploymentStatus', on_delete=models.PROTECT, related_name='employees')
    employee_type = models.ForeignKey('teamcentral.EmployeeType', on_delete=models.PROTECT, related_name='employees')

    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    job_title = models.CharField(max_length=128, blank=True)
    approval_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    probation_end_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=50, blank=True, validators=[RegexValidator(r'^[A-Z0-9\-]{5,50}$')])
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    gender = models.CharField(max_length=20, choices=[('MALE', 'Male'), ('FEMALE', 'Female'),
        ('OTHER', 'Other'), ('PREFER_NOT_TO_SAY', 'Prefer not to say')], blank=True)
    marital_status = models.CharField(max_length=20, choices=[
        ('SINGLE', 'Single'), ('MARRIED', 'Married'),
        ('DIVORCED', 'Divorced'), ('WIDOWED', 'Widowed'),
        ('PREFER_NOT_TO_SAY', 'Prefer not to say')], blank=True)
    bank_details = models.JSONField(null=True, blank=True)
    preferences = models.JSONField(null=True, blank=True)
    notes = models.TextField(blank=True)
    address_display = models.CharField(max_length=255, blank=True, editable=False)
    sso_provider = models.CharField(max_length=20, choices=[('GOOGLE', 'Google'), ('APPLE', 'Apple'), ('EMAIL', 'Email')], blank=True)
    sso_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_unsubscribed = models.BooleanField(default=False)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    groups = models.ManyToManyField('auth.Group', related_name='employee_groups', blank=True)
    user_permissions = models.ManyToManyField('auth.Permission', related_name='employee_permissions', blank=True)

    history = HistoricalRecords()

    class Meta:
        indexes = [
            models.Index(fields=['employee_code'], name='employee_code_idx'),
            models.Index(fields=['email', 'username'], name='employee_email_username_idx'),
            models.Index(fields=['department', 'role', 'team'], name='employee_dept_role_team_idx'),
            GinIndex(fields=['bank_details'], name='employee_bank_details_gin_idx'),
            models.Index(fields=['sso_id'], name='employee_sso_id_idx'),
            models.Index(fields=['sso_provider', 'is_verified'], name='employee_sso_verified_idx'),
            GinIndex(fields=['preferences'], name='employee_preferences_gin_idx'),
        ]

    def __str__(self):
        return f"{self.get_full_name}"

    def clean(self):
        if self.employment_status.code == 'ACTV' and not self.hire_date:
            raise ValidationError("Active employees must have a hire date.")

        # if self.employment_status and self.employment_status.code == 'ACTV' and not self.hire_date:
            # 🟡 Just log a warning instead of blocking save
            # logger.warning("Active employee has no hire_date — skipping validation due to UI limits.")
            # Optionally auto-set today's date (comment out if not desired)
            # self.hire_date = timezone.now().date()

        # SSO logic
        if self.sso_provider in ['GOOGLE', 'APPLE'] and not self.sso_id:
            raise ValidationError("sso_id is required for SSO providers.")
        if self.sso_provider == 'EMAIL':
            # normalize for email users
            self.sso_id = None

        super().clean()

    def save(self, *args, **kwargs):
        """Override save to handle user parameter for audit fields and generate employee_code if not set."""
        user = kwargs.pop('user', None)  # Remove 'user' from kwargs
        if user and isinstance(user, get_user_model()):
            if not self.pk:  # New instance
                self.created_by = user
            self.updated_by = user

        # Normalize sso_id: treat empty string as None so unique + null=True works
        if self.sso_id == '':
            self.sso_id = None

        # Generate employee_code if not set
        if not self.employee_code:
            max_attempts = 10
            for attempt in range(max_attempts):
                code_suffix = str(uuid.uuid4()).replace('-', '')[:12].upper()
                employee_code = f"DJP{code_suffix}"
                if not Employee.all_objects.filter(employee_code=employee_code).exists():
                    self.employee_code = employee_code
                    logger.info(f"Generated unique employee_code in save: {employee_code}")
                    break
                logger.warning(f"Employee code collision in save: {employee_code}, attempt {attempt + 1}")
            else:
                logger.error("Failed to generate unique employee code in save.")
                raise ValueError("Unable to generate unique employee code.")

        super().save(*args, **kwargs)  # Call parent save without user

    @transaction.atomic
    def soft_delete(self, user=None, reason=None):
        """Soft delete employee."""
        from users.exceptions import EmployeeValidationError
        logger.info(f"Soft deleting Employee: {self.employee_code}, user={user}")
        if not self.is_active:
            raise EmployeeValidationError(
                "Cannot delete inactive employee.",
                code="inactive_employee",
                details={"employee_id": self.pk}
            )
        self.deleted_at = timezone.now()
        self.deleted_by = user  # Set deleted_by directly
        self.employment_status = EmploymentStatus.objects.get(code='TERM')
        self.termination_date = timezone.now().date()
        self.is_active = False
        try:
            super().save()  # Call save without user
            logger.info(f"Employee soft deleted: {self.employee_code}")
        except Exception as e:
            logger.error(f"Failed to soft delete employee {self.employee_code}: {str(e)}")
            raise EmployeeValidationError(
                f"Failed to soft delete employee: {str(e)}",
                code="employee_soft_delete_error",
                details={"error": str(e)}
            )

    @transaction.atomic
    def restore(self, user=None):
        """Restore soft-deleted employee."""
        from users.exceptions import EmployeeValidationError
        logger.info(f"Restoring Employee: {self.employee_code}, user={user}")
        self.deleted_at = None
        self.deleted_by = None
        self.employment_status = EmploymentStatus.objects.get(code='ACTV')
        self.termination_date = None
        self.is_active = True
        try:
            super().save()  # Call save without user
            logger.info(f"Employee restored: {self.employee_code}")
        except Exception as e:
            logger.error(f"Failed to restore employee {self.employee_code}: {str(e)}")
            raise EmployeeValidationError(
                f"Failed to restore employee: {str(e)}",
                code="employee_restore_error",
                details={"error": str(e)}
            )

    @property
    def is_active_employee(self):
        today = timezone.now().date()
        return (
            self.employment_status.code == 'ACTV' and
            self.hire_date and
            self.hire_date <= today and
            (self.termination_date is None or self.termination_date > today)
        )


    @property
    def get_full_name(self):
        """Return full name or username."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username

    @property
    def role_rank(self):
        """Return role hierarchy rank."""
        return self.role.rank if self.role else len(Role.objects.all())

    def can_approve_invoice(self, invoice_amount):
        """Check if employee can approve invoice amount."""
        return Decimal(invoice_amount) <= self.approval_limit

    @property
    def timezone(self):
        """Default to UTC."""
        return 'UTC'

    @property
    def is_soft_deleted(self):
        return getattr(self, "deleted_at", None) is not None or getattr(self, "is_active", True) is False

    @property
    def is_verified_account(self):
        # if your attribute is `is_verified`, use that; adapt to your actual attribute
        return bool(getattr(self, "is_verified", False))
