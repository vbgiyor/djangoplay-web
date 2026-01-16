import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone
from entities.models import Entity
from simple_history.models import HistoricalRecords

from invoices.constants import BILLING_FREQUENCY_CHOICES, BILLING_STATUS_CODES, DESCRIPTION_MAX_LENGTH
from invoices.exceptions import InvoiceValidationError

logger = logging.getLogger(__name__)

class BillingSchedule(TimeStampedModel, AuditFieldsModel):

    """Model representing a recurring or scheduled billing plan for invoices."""

    id = models.AutoField(primary_key=True)
    entity = models.ForeignKey(
        Entity,
        on_delete=models.PROTECT,
        related_name='billing_schedules',
        help_text="Entity associated with this billing schedule."
    )
    description = models.CharField(
        max_length=DESCRIPTION_MAX_LENGTH,
        help_text="Description of the billing schedule (e.g., 'Monthly subscription')."
    )
    frequency = models.CharField(
        max_length=20,
        choices=BILLING_FREQUENCY_CHOICES,
        help_text="Frequency of billing (e.g., MONTHLY, QUARTERLY)."
    )
    start_date = models.DateField(
        default=timezone.now,
        help_text="Start date of the billing schedule."
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="End date of the billing schedule (optional)."
    )
    next_billing_date = models.DateField(
        help_text="Date for the next scheduled invoice."
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Fixed amount to be billed per cycle."
    )
    status = models.CharField(
        max_length=20,
        choices=[(k, v) for k, v in BILLING_STATUS_CODES.items()],
        default='ACTIVE',
        help_text="Status of the billing schedule (e.g., ACTIVE, PAUSED, COMPLETED)."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'billing_schedule'
        ordering = ['-start_date', 'entity']
        verbose_name = "Billing Schedule"
        verbose_name_plural = "Billing Schedules"
        constraints = [
            models.UniqueConstraint(
                fields=['entity', 'description', 'start_date'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_billing_schedule'
            ),
            models.CheckConstraint(
                check=models.Q(amount__gte=0),
                name='non_negative_amount'
            ),
        ]
        indexes = [
            models.Index(fields=['entity', 'frequency']),
            models.Index(fields=['start_date', 'next_billing_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.description} for {self.entity.name}"

    def clean(self):
        """Validate BillingSchedule fields."""
        logger.debug(f"Validating BillingSchedule: {self.description or 'Unnamed'}")

        if not self.description or not self.description.strip():
            raise InvoiceValidationError(
                message="Description cannot be empty or whitespace.",
                code="empty_description",
                details={"field": "description"}
            )

        if not self.start_date:
            raise InvoiceValidationError(
                message="Start date is required.",
                code="missing_start_date",
                details={"field": "start_date"}
            )

        # Skip validation if being soft-deleted
        if hasattr(self, 'is_active') and not self.is_active and self.deleted_at is not None:
            logger.debug("Skipping duplicate validation for soft-deleted BillingSchedule")
            return

        # Check for duplicate entity, description, and start_date (only active records)
        existing_schedules = BillingSchedule.objects.filter(
            entity=self.entity,
            description__iexact=self.description,
            start_date=self.start_date
        )
        if self.pk:
            existing_schedules = existing_schedules.exclude(pk=self.pk)

        if existing_schedules.exists():
            raise InvoiceValidationError(
                message="A billing schedule with this entity, description, and start date already exists.",
                code="invalid_billing_schedule",
                details={"fields": ["entity", "description", "start_date"]}
            )

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save billing schedule with audit logging and atomic transaction."""
        logger.debug(f"Saving BillingSchedule: {self.description or 'New Schedule'}, user={user}")
        if not skip_validation:
            self.clean()
        User = get_user_model()
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        try:
            super().save(*args, **kwargs)
            logger.info(f"BillingSchedule saved successfully: {self} (ID: {self.pk})")
        except Exception as e:
            logger.error(f"Failed to save BillingSchedule: {self.description or 'ERROR'}, error: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to save billing schedule: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )
        return self

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete billing schedule with atomic transaction."""
        logger.info(f"Soft deleting BillingSchedule: {self.description}, user={user}")
        if not self.is_active:
            raise InvoiceValidationError(
                message="Cannot perform operation on an inactive billing schedule.",
                code="inactive_billing_schedule",
                details={"billing_schedule_id": self.pk}
            )
        self.deleted_by = user
        self.is_active = False
        self.deleted_at = timezone.now()
        try:
            super().soft_delete()
            logger.info(f"Successfully soft deleted {self.description}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete {self.description}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to soft delete billing schedule: {str(e)}",
                code="soft_delete_error",
                details={"error": str(e)}
            )

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted billing schedule with atomic transaction."""
        logger.info(f"Restoring BillingSchedule: {self.description}, user={user}")
        try:
            super().restore()
            self.status = 'ACTIVE'
            self.updated_by = user
            self.save(user=user)
            logger.info(f"Successfully restored {self.description}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore {self.description}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to restore billing schedule: {str(e)}",
                code="restore_error",
                details={"error": str(e)}
            )
