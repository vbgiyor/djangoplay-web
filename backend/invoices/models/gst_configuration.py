import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.auth import get_user_model
from django.db import models, transaction
from locations.models import CustomCountry, CustomRegion
from simple_history.models import HistoricalRecords

from invoices.constants import DESCRIPTION_MAX_LENGTH, GST_RATE_TYPE_CHOICES
from invoices.exceptions import GSTValidationError
from invoices.models.generic_gst_fields import GenericGSTFields
from invoices.services import validate_gst_configuration

logger = logging.getLogger(__name__)

class GSTConfiguration(GenericGSTFields, TimeStampedModel, AuditFieldsModel):

    """Model representing GST tax rate configurations for invoices."""

    id = models.AutoField(primary_key=True)
    description = models.CharField(
        max_length=DESCRIPTION_MAX_LENGTH,
        help_text="Description of the GST configuration (e.g., 'Standard GST for electronics')."
    )
    rate_type = models.CharField(
        max_length=20,
        choices=GST_RATE_TYPE_CHOICES,
        default='STANDARD',
        help_text="Type of GST rate (e.g., STANDARD, EXEMPT, ZERO_RATED)."
    )
    applicable_region = models.ForeignKey(
        CustomRegion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Region where this GST configuration applies (optional, for state-specific rates)."
    )
    effective_from = models.DateField(
        help_text="Date from which this GST configuration is effective."
    )
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text="Date until which this GST configuration is effective (optional)."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'gst_configuration'
        ordering = ['-effective_from']
        verbose_name = "GST Configuration"
        verbose_name_plural = "GST Configurations"
        constraints = [
            models.UniqueConstraint(
                fields=['applicable_region', 'effective_from', 'rate_type'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_gst_config'
            )
        ]
        indexes = [
            models.Index(fields=['applicable_region', 'effective_from', 'rate_type']),
            models.Index(fields=['rate_type']),
            models.Index(fields=['effective_from', 'effective_to']),
        ]

    def __str__(self):
        return f"GST Config: {self.description} ({self.rate_type or self.applicable_region})"

    def clean(self):
        logger.debug(f"Validating GSTConfiguration: {self.description or 'Unknown'}")
        if self.applicable_region and not self.applicable_region.is_active:
            raise GSTValidationError(
                message="Region must be active.",
                code="inactive_region",
                details={"field": "applicable_region", "region_id": self.applicable_region.id}
            )

        if any([self.cgst_amount, self.sgst_amount, self.igst_amount]):
            raise GSTValidationError(
                message="GST amount fields must be zero for GST configurations.",
                code="invalid_gst_amounts",
                details={"fields": ["cgst_amount", "sgst_amount", "igst_amount"]}
            )

        try:
            # Try fetching India by country code or name
            billing_country = CustomCountry.objects.filter(
                models.Q(country_code__iexact='IN') | models.Q(name__iexact='India'),
                is_active=True
            ).first()
            if not billing_country:
                logger.warning("India country not found; skipping GST validation")
                return  # Skip GST validation if India is not found
        except CustomCountry.DoesNotExist:
            logger.warning("India country not found; skipping GST validation")
            return  # Skip GST validation if India is not found

        # Determine if inter-state based on applicable_region
        is_interstate = not self.applicable_region  # Assume inter-state if no region specified

        if is_interstate and (self.cgst_rate or self.sgst_rate):
            raise GSTValidationError(
                message="Inter-state GST configurations must only have IGST rate.",
                code="invalid_gst_rates",
                details={"cgst_rate": self.cgst_rate, "sgst_rate": self.sgst_rate}
            )
        elif not is_interstate and self.igst_rate:
            raise GSTValidationError(
                message="Intra-state GST configurations must only have CGST and SGST rates.",
                code="invalid_gst_rates",
                details={"igst_rate": self.igst_rate}
            )

        from decimal import Decimal
        self.clean_tax_fields(
            has_gst_required_fields=True,
            billing_region_id=self.applicable_region.id if self.applicable_region else None,
            billing_country=billing_country,
            issue_date=self.effective_from,
            tax_exemption_status=self.rate_type,
            base_amount=Decimal('0.00')
        )

        try:
            validate_gst_configuration(self, exclude_pk=self.id)
        except GSTValidationError as e:
            logger.error(f"Validation failed: {str(e)}")
            raise GSTValidationError(
                message=f"Validation failed: {str(e)}",
                code="gst_validation_error",
                details={"error": str(e)}
            )

    # @transaction.atomic
    # def save(self, *args, user=None, skip_validation=False, **kwargs):
    #     """Save GST configuration with audit logging and atomic transaction."""
    #     logger.debug(f"Saving GSTConfiguration: {self.description}, user={user}")
    #     if not skip_validation:
    #         self.clean()
    #     User = get_user_model()
    #     if user and isinstance(user, User):
    #         if not self.pk:
    #             self.created_by = user
    #         self.updated_by = user
    #     try:
    #         super().save(*args, **kwargs)
    #         logger.info(f"GSTConfiguration saved successfully: {self} (ID: {self.pk})")
    #     except Exception as e:
    #         logger.error(f"Failed to save GSTConfiguration: {self.description}, error: {str(e)}", exc_info=True)
    #         raise GSTValidationError(
    #             message=f"Failed to save GST configuration: {str(e)}",
    #             code="gst_validation_error",
    #             details={"error": str(e)}
    #         )
    #     return self

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save GST configuration with audit logging and atomic transaction."""
        logger.debug(f"Saving GSTConfiguration: {self.description}, user={user}, skip_validation={skip_validation}")
        User = get_user_model()
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        try:
            if not skip_validation:
                self.clean()
            super().save(*args, **kwargs)
            logger.info(f"GSTConfiguration saved successfully: {self} (ID: {self.pk})")
        except Exception as e:
            logger.error(f"Failed to save GSTConfiguration: {self.description}, error: {str(e)}", exc_info=True)
            raise GSTValidationError(
                message=f"Failed to save GST configuration: {str(e)}",
                code="gst_validation_error",
                details={"error": str(e)}
            )
        return self

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete GST configuration with atomic transaction."""
        logger.info(f"Soft deleting GSTConfiguration: {self.description}, user={user}")
        if not self.is_active:
            raise GSTValidationError(
                message="Cannot perform operation on an inactive GST configuration.",
                code="inactive_gst_config",
                details={"config_id": self.id}
            )
        self.deleted_by = user
        try:
            super().soft_delete()
            logger.info(f"Successfully soft deleted {self.description}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete {self.description}: {str(e)}", exc_info=True)
            raise GSTValidationError(
                message=f"Failed to soft delete GST configuration: {str(e)}",
                code="gst_sof_delete_error",
                details={"error": str(e)}
            )

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted GST configuration with atomic transaction."""
        logger.info(f"Restoring GSTConfiguration: {self.description}, user={user}")
        if self.is_active:
            raise GSTValidationError(
                message="Cannot restore an active GST configuration.",
                code="already_active_gst_configuration",
                details={"gst_configuration_id": self.pk}
            )
        try:
            self.is_active = True
            self.deleted_at = None
            self.updated_by = user
            self.save(user=user)
            logger.info(f"Successfully restored {self.description}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore {self.description}: {str(e)}", exc_info=True)
            raise GSTValidationError(
                message=f"Failed to restore GST configuration: {str(e)}",
                code="gst_restore_error",
                details={"error": str(e)}
            )
