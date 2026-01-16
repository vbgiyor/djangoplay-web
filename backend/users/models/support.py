import logging
import uuid

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse
from django.utils import timezone
from simple_history.models import HistoricalRecords

from .employee import Employee

logger = logging.getLogger(__name__)

class SupportStatus(models.TextChoices):

    """Choices for support ticket status."""

    OPEN = 'OPEN', 'Open'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    RESOLVED = 'RESOLVED', 'Resolved'
    CLOSED = 'CLOSED', 'Closed'


class Severity(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class SupportTicket(TimeStampedModel, AuditFieldsModel):

    """Model for storing support tickets raised by employees or members."""

    id = models.AutoField(primary_key=True)
    ticket_number = models.CharField(
        max_length=15,
        unique=True,
        help_text='Unique Ticket Number (SUP + 12 hex chars)',
        editable=False
    )
    subject = models.CharField(max_length=200, help_text='Ticket subject')
    full_name = models.CharField(max_length=100, help_text='Submitter full name')
    email = models.EmailField(help_text='Submitter email address')
    message = models.TextField(help_text='Support request message')
    status = models.CharField(
        max_length=20,
        choices=SupportStatus.choices,
        default=SupportStatus.OPEN,
        help_text='Ticket status'
    )
    resolved_at = models.DateTimeField(null=True, blank=True, help_text='Resolution timestamp')
    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        related_name='support_tickets',
        null=True,
        blank=True,
        help_text='Associated employee (if authenticated user)'
    )
    file_uploads = GenericRelation('users.FileUpload', related_query_name='support_ticket')
    severity = models.CharField(max_length=10, choices=Severity.choices, null=True, blank=True)
    is_bug_report = models.BooleanField(default=False, help_text="True if this is a bug report")
    emails_sent = models.BooleanField(
        default=False,
        help_text="True if email have been sent"
    )
    client_ip = models.GenericIPAddressField(
        protocol='both',  # allows IPv4 & IPv6
        unpack_ipv4=False,
        null=True,
        blank=True
    )
    github_issue = models.URLField(blank=True, null=True)
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=['ticket_number'], name='support_ticket_number_idx'),
            models.Index(fields=['email'], name='support_email_idx'),
            models.Index(fields=['status'], name='support_status_idx'),
            models.Index(fields=['employee'], name='support_employee_idx'),
        ]
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'

    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.subject[:50]}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            max_attempts = 10
            for attempt in range(max_attempts):
                prefix = "B" if self.is_bug_report else "S"
                code_suffix = str(uuid.uuid4()).replace('-', '')[:12].upper()
                ticket_number = f"{prefix}{code_suffix}"
                if not SupportTicket.all_objects.filter(ticket_number=ticket_number).exists():
                    self.ticket_number = ticket_number
                    break
                logger.warning(f"Ticket number collision: {ticket_number}, attempt {attempt + 1}")
            else:
                logger.error("Failed to generate unique ticket number.")
                raise ValueError("Unable to generate unique ticket number.")

        if self.status == SupportStatus.RESOLVED or self.status == SupportStatus.CLOSED:
            if not self.resolved_at:
                self.resolved_at = timezone.now()
            # self.is_active = False
        else:
            # self.is_active = True
            pass

        user = kwargs.pop('user', None)
        if user and isinstance(user, get_user_model()):
            if not self.pk:  # New instance
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"SupportTicket saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete support ticket."""
        logger.info(f"Soft deleting SupportTicket: {self.ticket_number}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(user=user)

    def get_admin_change_url(self):
        """Return just the path (for templates that build full URL)."""
        return reverse('admin:users_supportticket_change', args=[self.pk])
