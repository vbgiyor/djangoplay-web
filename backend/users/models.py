from decimal import Decimal

from core.models import ActiveManager, TimeStampedModel
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        with transaction.atomic():
            extra_fields.setdefault('is_staff', False)
            extra_fields.setdefault('is_superuser', False)
            if not username:
                raise ValueError('The Username field must be set')
            if not email:
                raise ValueError('The Email field must be set')
            email = self.normalize_email(email)
            user = self.model(username=username, email=email, **extra_fields)
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            user.save(using=self._db)
            return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'CEO')
        extra_fields.setdefault('approval_limit', Decimal('99999999.99'))
        extra_fields.setdefault('region', 'South Asia')
        extra_fields.setdefault('timezone', 'Asia/Kolkata')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(username, email, password, **extra_fields)

class User(TimeStampedModel, AbstractUser):
    objects = UserManager()
    active_users = ActiveManager()
    all_users = models.Manager()

    DEPARTMENT_CHOICES = [
        ('AP', 'Accounts Payable'),
        ('AR', 'Accounts Receivable'),
        ('AUD', 'Audit'),
        ('FIN', 'Finance'),
        ('MGT', 'Management'),
        ('OT', 'Other'),
    ]

    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('ACCOUNTANT', 'Accountant'),
        ('MANAGER', 'Manager'),
        ('AUDITOR', 'Auditor'),
        ('CLERK', 'Clerk'),
        ('CEO', 'CEO'),
    ]

    id = models.AutoField(primary_key=True)
    employee_code = models.CharField(
        max_length=15,
        unique=True,
        validators=[RegexValidator(r'^DJP\d{10}$', message='Employee Code must be in the format DJP1234567890')],
        help_text='Unique Employee Code in the format DJP1234567890',
        editable=False
    )
    department = models.CharField(max_length=3, choices=DEPARTMENT_CHOICES, default='OT')
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(r'^\+?[1-9]\d{7,14}$', message='Phone number must be valid.')]
    )
    job_title = models.CharField(max_length=128, blank=True)
    region = models.CharField(max_length=100, blank=True, help_text="Geographic region or location")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CLERK')
    approval_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Maximum amount user can approve'
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
        help_text='Manager of this employee'
    )
    created_by = models.ForeignKey(
        'self',
        related_name='created_by_user',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    updated_by = models.ForeignKey(
        'self',
        related_name='updated_by_user',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, help_text='Upload a profile photo')
    timezone = models.CharField(max_length=100, default='IST', help_text='User time zone for multi-region teams')

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['employee_code']),
            models.Index(fields=['email', 'username']),
            models.Index(fields=['department', 'role'])
        ]
        constraints = [
            models.UniqueConstraint(fields=['employee_code'], name='unique_employee_code')
        ]

    def __str__(self):
        return f"{self.get_full_name} ({self.employee_code})"

    def save(self, *args, **kwargs):
        self.email = self.email.lower()

        # Save first if no id (i.e., on initial save)
        if not self.id:
            super().save(*args, **kwargs)

        if not self.employee_code:
            self.employee_code = f"DJP{self.id:010d}"
            # Save again to update the employee_code with a valid id
            super().save(update_fields=['employee_code'])

        else:
            super().save(*args, **kwargs)

    @classmethod
    def get_active_users(cls):
        return cls.active_users.all()

    @property
    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username

    @property
    def get_role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    def can_approve_invoice(self, invoice_amount):
        return Decimal(invoice_amount) <= self.approval_limit

    def clean(self):
        if self.manager == self:
            raise ValidationError("An employee cannot be their own manager.")
        super().clean()

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.deleted_at = None
        self.save()
