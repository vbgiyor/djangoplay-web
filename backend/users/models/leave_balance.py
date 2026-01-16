import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from .employee import Employee
from .leave_type import LeaveType

logger = logging.getLogger(__name__)

class LeaveBalance(TimeStampedModel, AuditFieldsModel):

    """Model for employee leave balances."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_balances',
        help_text='Employee'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='balances',
        help_text='Leave type'
    )
    year = models.PositiveIntegerField(help_text='Year of balance')
    balance = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text='Total leave balance in hours'
    )
    used = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text='Used leave in hours'
    )
    reset_date = models.DateField(help_text='Date when balance was reset')
    history = HistoricalRecords()


    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Leave Balance"
        verbose_name_plural = "Leave Balances"
        indexes = [
            models.Index(fields=['employee', 'leave_type', 'year'], name='leave_balance_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['employee', 'leave_type', 'year'], name='unique_leave_balance')
        ]

    def __str__(self):
        return f"{self.employee.employee_code} - {self.leave_type.code} ({self.year})"

    def clean(self):
        """Validate leave balance fields."""
        logger.debug(f"Cleaning LeaveBalance: employee={self.employee.employee_code}, year={self.year}")
        if self.balance < self.used:
            raise ValueError("Used leave cannot exceed balance.")
        if self.year > timezone.now().year + 1:
            raise ValueError("Year cannot be more than one year in the future.")
        super().clean()

    def save(self, *args, user=None, **kwargs):
        """Save with audit fields."""
        self.clean()
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"LeaveBalance saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete leave balance."""
        logger.info(f"Soft deleting LeaveBalance: {self}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(user=user)
