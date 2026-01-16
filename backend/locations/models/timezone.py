import logging
import re

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords
from utilities.utils.general.normalize_text import normalize_text

from .custom_country import CustomCountry

logger = logging.getLogger(__name__)

def validate_offset(value):
    """Validate that the offset is between -12.0 and +14.0 and is a multiple of 0.25."""
    if not (-12.0 <= value <= 14.0):
        raise ValidationError(f"Offset must be between -12.0 and 14.0, got {value}.")
    if round(value * 4) / 4 != value:
        raise ValidationError(f"Offset must be a multiple of 0.25, got {value}.")

def validate_timezone_id(value):
    """Validate IANA timezone ID format."""
    if not re.match(r'^[A-Za-z0-9/_+-]+$', value):
        raise ValidationError(f"Invalid timezone ID format: {value}.")

def validate_country_code(value):
    """Validate that the country code exists in CustomCountry."""
    if value and not CustomCountry.objects.filter(country_code=value).exists():
        raise ValidationError(f"Country code '{value}' does not exist in CustomCountry.")

class Timezone(TimeStampedModel, AuditFieldsModel):

    """Timezone model with audit fields and IANA timezone support."""

    id = models.BigAutoField(primary_key=True)
    timezone_id = models.CharField(
        max_length=100,
        unique=True,
        validators=[validate_timezone_id],
        help_text="IANA Time Zone ID (e.g., 'Asia/Kolkata')"
    )
    gmt_offset_jan = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[validate_offset],
        help_text="GMT offset in January (hours, e.g., 5.5)"
    )
    dst_offset_jul = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[validate_offset],
        help_text="DST offset in July (hours, e.g., 5.5)"
    )
    raw_offset = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[validate_offset],
        help_text="Standard time offset without DST (hours, e.g., 5.5)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indicates if the timezone is currently in use"
    )
    display_name = models.CharField(
        max_length=150,
        help_text="Human-readable timezone name (e.g., 'India Standard Time')"
    )
    country_code = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        validators=[
            RegexValidator(r'^[A-Z]{2}$', "Country code must be two uppercase letters."),
            validate_country_code
        ],
        help_text="ISO 3166-1 alpha-2 country code from CustomCountry (e.g., 'IN' for India)"
    )
    history = HistoricalRecords(excluded_fields=['id'])

    objects = ActiveManager()

    class Meta:
        app_label = 'locations'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['country_code']),
        ]
        verbose_name = "Timezone"
        verbose_name_plural = "Timezones"

    def __str__(self):
        return f"{self.timezone_id} ({self.display_name})"

    def clean(self):
        """Validate timezone data."""
        if not self.timezone_id:
            raise ValidationError("Timezone ID is required.")
        if not self.display_name:
            raise ValidationError("Display name is required.")

        # Validate offsets
        if self.gmt_offset_jan is None:
            raise ValidationError("GMT offset for January is required.")
        if self.dst_offset_jul is None:
            raise ValidationError("DST offset for July is required.")
        if self.raw_offset is None:
            raise ValidationError("Raw offset is required.")

        # Normalize the display name if needed
        self.display_name = normalize_text(self.display_name)



    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save timezone with audit logging."""
        logger.debug(f"Saving Timezone: {self.timezone_id}, user={user}")
        if not skip_validation:
            self.clean()
        User = get_user_model()
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by_id = user.pk
            self.updated_by_id = user.pk
        try:
            super().save(*args, **kwargs)
            logger.info(f"Successfully saved Timezone: {self.timezone_id} (ID: {self.pk})")
        except Exception as e:
            logger.error(f"Failed to save Timezone: {self.timezone_id}, error: {str(e)}", exc_info=True)
            raise
        return self

    def soft_delete(self, user=None):
        """Soft delete timezone with validation and audit logging."""
        logger.debug(f"Attempting to soft delete Timezone: {self.timezone_id}, user={user}")
        if not self.is_active or self.deleted_at:
            logger.warning(f"Timezone {self.timezone_id} is already soft-deleted")
            return self

        User = get_user_model()
        if user and not isinstance(user, User):
            logger.error(f"Invalid user provided for soft delete: {user}")
            raise ValidationError("Invalid user provided for soft delete")

        self.is_active = False
        self.deleted_at = timezone.now()
        self.deleted_by_id = user.pk
        self.updated_by_id = user.pk
        try:
            self.save(skip_validation=True)
            logger.info(f"Successfully soft-deleted Timezone: {self.timezone_id}, user={user}")
        except Exception as e:
            logger.error(f"Failed to soft-delete Timezone: {self.timezone_id}, error: {str(e)}", exc_info=True)
            raise
        return self

    def restore(self, user=None):
        """Restore a soft-deleted timezone with validation and audit logging."""
        logger.debug(f"Attempting to restore Timezone: {self.timezone_id}, user={user}")
        if self.is_active and not self.deleted_at:
            logger.warning(f"Timezone {self.timezone_id} is already active")
            return self

        User = get_user_model()
        if user and not isinstance(user, User):
            logger.error(f"Invalid user provided for restore: {user}")
            raise ValidationError("Invalid user provided for restore")

        self.is_active = True
        self.deleted_at = None
        self.deleted_by_id = None
        self.updated_by_id = user.pk
        try:
            self.save(skip_validation=True)
            logger.info(f"Successfully restored Timezone: {self.timezone_id}, user={user}")
        except Exception as e:
            logger.error(f"Failed to restore Timezone: {self.timezone_id}, error: {str(e)}", exc_info=True)
            raise
        return self
