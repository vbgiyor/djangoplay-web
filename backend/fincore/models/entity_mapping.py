import logging
import uuid

from core.models.LifecycleModel import TimeStampedModel
from django.db import models, transaction
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)

class FincoreEntityMapping(TimeStampedModel):

    """Model to map fincore resources to any entity-like object."""

    entity_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique UUID for the entity mapping."
    )
    entity_type = models.CharField(
        max_length=50,
        help_text="Type of entity (e.g., 'entities.Entity', 'vendors.Vendor')."
    )
    entity_id = models.CharField(
        max_length=100,
        help_text="ID of the entity in its app."
    )
    content_type = models.CharField(
        max_length=100,
        help_text="App and model name (e.g., 'entities.Entity')."
    )
    history = HistoricalRecords()

    class Meta:
        db_table = 'fincore_entity_mapping'
        verbose_name = "Fincore Entity Mapping"
        verbose_name_plural = "Fincore Entity Mappings"
        unique_together = ('entity_type', 'entity_id')
        indexes = [
            models.Index(fields=['entity_uuid']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['entity_type', 'entity_id', 'entity_uuid'], name='entity_mapping_lookup_idx'),
        ]

    def __str__(self):
        return f"{self.entity_type}:{self.entity_id} ({self.entity_uuid})"

    @transaction.atomic
    def save(self, *args, **kwargs):
        """Save entity mapping with atomic transaction."""
        super().save(*args, **kwargs)
