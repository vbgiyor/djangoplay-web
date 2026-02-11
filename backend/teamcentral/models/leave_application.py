import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords

from .leave_type import LeaveType

logger = logging.getLogger(__name__)

class LeaveApplication(TimeStampedModel, AuditFieldsModel):

    """Model for employee leave applications."""

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_applications',
        help_text='Employee'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='applications',
        help_text='Leave type'
    )
    start_date = models.DateField(help_text='Start date of leave')
    end_date = models.DateField(null=True, blank=True, help_text='End date of leave')
    hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Leave hours for partial-day'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
            ('CANCELLED', 'Cancelled')
        ],
        default='PENDING',
        help_text='Application status'
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves',
        help_text='Approver'
    )
    reason = models.TextField(blank=True, help_text='Reason for leave')
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Leave Application"
        verbose_name_plural = "Leave Applications"
        indexes = [
            models.Index(fields=['employee', 'status', 'start_date'], name='leave_application_idx'),
        ]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.leave_type.code} ({self.start_date})"

    def clean(self):
        """Validate leave application fields."""
        logger.debug(f"Cleaning LeaveApplication: employee={self.employee.employee_code}")
        if self.end_date and self.start_date > self.end_date:
            raise ValueError("End date must be after start date.")
        if self.hours and self.hours <= 0:
            raise ValueError("Hours must be positive.")
        if self.approver and not self.approver.is_active_employee:
            raise ValueError("Approver must be an active employee.")
        super().clean()

    def save(self, *args, user=None, **kwargs):
        """Save with audit fields."""
        self.clean()
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"LeaveApplication saved: {self}")

    @transaction.atomic
    def soft_delete(self, user=None, reason=None):
        """Soft delete leave application."""
        from users.exceptions import LeaveValidationError
        logger.info(f"Soft deleting LeaveApplication: {self}, user={user}")
        if not self.is_active:
            raise LeaveValidationError(
                "Cannot delete inactive leave application.",
                code="inactive_leave_application",
                details={"application_id": self.pk}
            )
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.status = 'CANCELLED'
        self.is_active = False
        try:
            super().save(user=user)
            logger.info(f"LeaveApplication soft deleted: {self}")
        except Exception as e:
            logger.error(f"Failed to soft delete leave application {self}: {str(e)}")
            raise LeaveValidationError(
                f"Failed to soft delete leave application: {str(e)}",
                code="leave_soft_delete_error",
                details={"error": str(e)}
            )

    @transaction.atomic
    def restore(self, user=None):
        """Restore soft-deleted leave application."""
        from users.exceptions import LeaveValidationError
        logger.info(f"Restoring LeaveApplication: {self}, user={user}")
        self.deleted_at = None
        self.deleted_by = None
        self.status = 'PENDING'
        self.is_active = True
        try:
            super().save(user=user)
            logger.info(f"LeaveApplication restored: {self}")
        except Exception as e:
            logger.error(f"Failed to restore leave application {self}: {str(e)}")
            raise LeaveValidationError(
                f"Failed to restore leave application: {str(e)}",
                code="leave_restore_error",
                details={"error": str(e)}
            )
