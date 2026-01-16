import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from ..exceptions import InvalidIndustryData

logger = logging.getLogger('industries')

class Industry(TimeStampedModel, AuditFieldsModel):

    """Model representing an ISIC Rev. 4 industry classification."""

    # Class-level setting to control __str__ format
    STR_FORMAT = 'description'  # Options: 'code', 'description', 'both'

    LEVEL_CHOICES = (
        ('SECTION', 'Section'),
        ('DIVISION', 'Division'),
        ('GROUP', 'Group'),
        ('CLASS', 'Class'),
    )

    SECTOR_CHOICES = (
        ('PRIMARY', 'Primary'),
        ('SECONDARY', 'Secondary'),
        ('TERTIARY', 'Tertiary'),
    )

    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=10, unique=True, help_text="ISIC code (e.g., 'A', '01', '011', '0111')")
    description = models.TextField(help_text="Description of the industry (e.g., 'Agriculture, forestry and fishing')")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, help_text="Hierarchy level (Section, Division, Group, Class)")
    sector = models.CharField(max_length=20, choices=SECTOR_CHOICES, help_text="Broader sector (e.g., Primary, Secondary, Tertiary)")
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent industry (e.g., Division for a Group, Group for a Class)"
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['code']
        verbose_name = "Industry"
        verbose_name_plural = "Industries"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['level']),
            models.Index(fields=['sector']),
            models.Index(fields=['parent']),
            models.Index(fields=['created_by']),
            models.Index(fields=['updated_by']),
            models.Index(fields=['deleted_by']),
        ]

    def __str__(self):
        """Return string representation based on STR_FORMAT."""
        if self.STR_FORMAT == 'code':
            return self.code
        elif self.STR_FORMAT == 'description':
            return self.description
        else:  # 'both' or any other value
            return f"{self.code} - {self.description}"

    def clean(self):
        errors = {}

        # Validate code format based on level
        if self.level == 'SECTION' and not (len(self.code) == 1 and self.code.isalpha()):
            errors['code'] = 'Section code must be a single letter.'
        elif self.level == 'DIVISION' and not (len(self.code) == 2 and self.code.isdigit()):
            errors['code'] = 'Division code must be 2 digits.'
        elif self.level == 'GROUP' and not (len(self.code) == 3 and self.code.isdigit()):
            errors['code'] = 'Group code must be 3 digits.'
        elif self.level == 'CLASS' and not (len(self.code) == 4 and self.code.isdigit()):
            errors['code'] = 'Class code must be 4 digits.'

        # Ensure parent is at the correct higher level
        if self.parent:
            if self.level == 'DIVISION' and self.parent.level != 'SECTION':
                errors['parent'] = 'Division parent must be a Section.'
            elif self.level == 'GROUP' and self.parent.level != 'DIVISION':
                errors['parent'] = 'Group parent must be a Division.'
            elif self.level == 'CLASS' and self.parent.level != 'GROUP':
                errors['parent'] = 'Class parent must be a Group.'
        elif self.level == 'CLASS' or self.level == 'GROUP' or self.level == 'DIVISION':
            # Optional stricter rule: non-section levels must have a parent
            # errors['parent'] = 'Non-Section industries must have a parent.'
            pass

        if self.level == 'SECTION' and self.parent is not None:
            errors['parent'] = 'Sections cannot have a parent.'

        # Validate sector based on section
        valid_sectors = {
            'A': 'PRIMARY',
            'C': 'SECONDARY',
            'G': 'TERTIARY',
            'H': 'TERTIARY',
            'I': 'TERTIARY',
            'J': 'TERTIARY',
            'K': 'TERTIARY',
            'L': 'TERTIARY',
        }
        if self.level == 'SECTION' and self.code in valid_sectors:
            expected_sector = valid_sectors[self.code]
            if self.sector != expected_sector:
                errors['sector'] = f'Sector for Section {self.code} must be {expected_sector}.'

        if not self.description or not self.description.strip():
            errors['description'] = 'Description cannot be empty.'

        if errors:
            # ✅ Use our domain exception
            logger.warning(f"Industry validation failed: {errors}")
            raise InvalidIndustryData(
                errors,
                code="invalid_fields",
                details={"model": "Industry", "code_value": self.code}
            )

        # Still call parent clean if needed
        try:
            super().clean()
        except ValidationError as e:
            # Wrap any generic validation as InvalidIndustryData
            logger.error(f"Industry super().clean() failed: {e}")
            raise InvalidIndustryData(
                e.message_dict if hasattr(e, "message_dict") else e.messages,
                code="invalid_industry_data",
                details={"model": "Industry"}
            )

    def save(self, *args, user=None, **kwargs):
        logger.info(f"Saving Industry: {self.code}, user={user}")
        try:
            self.clean()
        except InvalidIndustryData:
            # just re-raise to be caught at serializer/view level
            raise
        except ValidationError as e:
            # normalize any other ValidationError
            logger.error(f"Failed validation on save for Industry: {e}")
            raise InvalidIndustryData(
                e.message_dict if hasattr(e, "message_dict") else e.messages,
                code="invalid_industry_data",
                details={"model": "Industry", "operation": "save"}
            )

        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user

        try:
            super().save(*args, **kwargs)
            logger.info(f"Industry saved: {self}")
        except Exception as e:
            logger.error(f"Failed to save Industry: {e}", exc_info=True)
            raise

    def soft_delete(self, user=None, reason=None):
        """Soft delete industry with audit logging."""
        from industries.exceptions import InvalidIndustryData  # safe import

        logger.info(f"Soft deleting Industry: {self.code}, user={user}, reason={reason}")
        self.deleted_by = user
        try:
            super().soft_delete()
            logger.info(
                f"Successfully soft deleted {self.code}: "
                f"is_active={self.is_active}, deleted_at={self.deleted_at}"
            )
        except ValidationError as e:
            raise InvalidIndustryData(
                e.message_dict if hasattr(e, "message_dict") else e.messages,
                code="invalid_industry_data",
                details={"model": "Industry", "operation": "soft_delete"}
            )
        except Exception as e:
            logger.error(f"Failed to soft delete {self.code}: {str(e)}", exc_info=True)
            raise

    def restore(self, user=None, reason=None):
        """Restore a soft-deleted industry."""
        logger.info(f"Restoring Industry: {self.code}, user={user}, reason={reason}")
        self.deleted_by = None
        try:
            super().restore()
            logger.info(
                f"Successfully restored {self.code}: "
                f"is_active={self.is_active}, deleted_at={self.deleted_at}"
            )
        except ValidationError as e:
            raise InvalidIndustryData(
                e.message_dict if hasattr(e, "message_dict") else e.messages,
                code="invalid_industry_data",
                details={"model": "Industry", "operation": "restore"}
            )
        except Exception as e:
            logger.error(f"Failed to restore {self.code}: {str(e)}", exc_info=True)
            raise


    # def clean(self):
    #     # Validate code format based on level
    #     if self.level == 'SECTION' and not (len(self.code) == 1 and self.code.isalpha()):
    #         raise ValidationError({'code': 'Section code must be a single letter.'})
    #     elif self.level == 'DIVISION' and not (len(self.code) == 2 and self.code.isdigit()):
    #         raise ValidationError({'code': 'Division code must be 2 digits.'})
    #     elif self.level == 'GROUP' and not (len(self.code) == 3 and self.code.isdigit()):
    #         raise ValidationError({'code': 'Group code must be 3 digits.'})
    #     elif self.level == 'CLASS' and not (len(self.code) == 4 and self.code.isdigit()):
    #         raise ValidationError({'code': 'Class code must be 4 digits.'})

    #     # Ensure parent is at the correct higher level
    #     if self.parent:
    #         if self.level == 'DIVISION' and self.parent.level != 'SECTION':
    #             raise ValidationError({'parent': 'Division parent must be a Section.'})
    #         elif self.level == 'GROUP' and self.parent.level != 'DIVISION':
    #             raise ValidationError({'parent': 'Group parent must be a Division.'})
    #         elif self.level == 'CLASS' and self.parent.level != 'GROUP':
    #             raise ValidationError({'parent': 'Class parent must be a Group.'})
    #         elif self.level == 'SECTION' and self.parent is not None:
    #             raise ValidationError({'parent': 'Sections cannot have a parent.'})

    #     # Validate sector based on section
    #     valid_sectors = {
    #         'A': 'PRIMARY',
    #         'C': 'SECONDARY',
    #         'G': 'TERTIARY',
    #         'H': 'TERTIARY',
    #         'I': 'TERTIARY',
    #         'J': 'TERTIARY',
    #         'K': 'TERTIARY',
    #         'L': 'TERTIARY',
    #     }
    #     if self.level == 'SECTION' and self.code in valid_sectors and self.sector != valid_sectors[self.code]:
    #         raise ValidationError({'sector': f'Sector for Section {self.code} must be {valid_sectors[self.code]}.'})

    #     if not self.description or not self.description.strip():
    #         raise ValidationError({'description': 'Description cannot be empty.'})

    #     super().clean()

    # def save(self, *args, user=None, **kwargs):
    #     logger.info(f"Saving Industry: {self.code}, user={user}")
    #     self.clean()
    #     if user:
    #         if not self.pk:
    #             self.created_by = user
    #         self.updated_by = user
    #     try:
    #         super().save(*args, **kwargs)
    #         logger.info(f"Industry saved: {self}")
    #     except Exception as e:
    #         logger.error(f"Failed to save Industry: {e}")
    #         raise

    # def soft_delete(self, user=None, reason=None):
    #     """Soft delete industry with audit logging."""
    #     logger.info(f"Soft deleting Industry: {self.code}, user={user}")
    #     self.deleted_by = user
    #     try:
    #         super().soft_delete()
    #         logger.info(f"Successfully soft deleted {self.code}: is_active={self.is_active}, deleted_at={self.deleted_at}")
    #     except Exception as e:
    #         logger.error(f"Failed to soft delete {self.code}: {str(e)}", exc_info=True)
    #         raise

    # def restore(self, user=None, reason=None):
    #     """Restore a soft-deleted industry."""
    #     logger.info(f"Restoring Industry: {self.code}, user={user}")
    #     self.deleted_by = None
    #     try:
    #         super().restore()
    #         logger.info(f"Successfully restored {self.code}: is_active={self.is_active}, deleted_at={self.deleted_at}")
    #     except Exception as e:
    #         logger.error(f"Failed to restore {self.code}: {str(e)}", exc_info=True)
    #         raise
