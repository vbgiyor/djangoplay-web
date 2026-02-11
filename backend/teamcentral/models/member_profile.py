import logging
import uuid

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from .address import Address
from .member_status import MemberStatus

logger = logging.getLogger(__name__)

class MemberProfile(TimeStampedModel, AuditFieldsModel):

    """Model for storing external contact data (non-authenticated users)."""

    id = models.AutoField(primary_key=True)
    member_code = models.CharField(
        max_length=15,
        unique=True,
        help_text='Unique Member Code (MBR + 12 hex chars)',
        editable=False
    )
    email = models.EmailField(unique=True, help_text='Member email address')
    first_name = models.CharField(max_length=100, blank=True, help_text='First name')
    last_name = models.CharField(max_length=100, blank=True, help_text='Last name')
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text='Phone number in international format'
    )
    address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name='members',
        null=True,
        blank=True,
        help_text='Member address'
    )
    status = models.ForeignKey(
        'MemberStatus',
        on_delete=models.PROTECT,
        related_name='members',
        help_text='Member status'
    )
    address_display = models.CharField(max_length=255, blank=True, editable=False)
    employee = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='member_profile',
        help_text='Associated Employee for authentication'
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=['member_code'], name='member_code_idx'),
            models.Index(fields=['email'], name='member_email_idx'),
            models.Index(fields=['status'], name='member_status_idx'),
            models.Index(fields=['employee'], name='member_employee_idx'),
        ]

    def __str__(self):
        return f"{self.get_full_name} ({self.member_code})"

    def save(self, *args, user=None, **kwargs):
        """Generate member_code if not set and save with audit fields."""
        if not self.member_code:
            max_attempts = 10
            for attempt in range(max_attempts):
                code_suffix = str(uuid.uuid4()).replace('-', '')[:12].upper()
                member_code = f"MBR{code_suffix}"
                if not MemberProfile.all_objects.filter(member_code=member_code).exists():
                    self.member_code = member_code
                    logger.info(f"Generated unique member_code: {member_code}")
                    break
                logger.warning(f"Member code collision: {member_code}, attempt {attempt + 1}")
            else:
                logger.error("Failed to generate unique member code.")
                raise ValueError("Unable to generate unique member code.")
        self.clean()
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"Member saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete member."""
        logger.info(f"Soft deleting Member: {self.member_code}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.status = MemberStatus.objects.get(code='SUSP')
        self.save(user=user)

    def restore(self, user=None):
        self.deleted_at = None
        self.deleted_by = None
        self.status = MemberStatus.objects.get(code='ACTV')
        self.save(user=user)

    @property
    def get_full_name(self):
        """Return full name or email."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email
