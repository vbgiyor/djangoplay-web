import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)

class AuditFieldsModel(models.Model):

    """
    An abstract base class that provides audit fields for tracking
    who created, updated, and deleted an object.

    The %(class)s placeholder in related_name ensures uniqueness across
    all models that inherit from this class.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Use string reference instead of get_user_model()
        related_name='%(app_label)s_%(class)s_created_by',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who created this object."
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Use string reference
        related_name='%(app_label)s_%(class)s_updated_by',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who last updated this object."
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Use string reference
        related_name='%(app_label)s_%(class)s_deleted_by',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who deleted this object."
    )

    class Meta:
        abstract = True
