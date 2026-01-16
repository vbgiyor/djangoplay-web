import mimetypes

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords


class FileUpload(TimeStampedModel, AuditFieldsModel,):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    file = models.FileField(
        upload_to='file_uploads/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    'jpg', 'jpeg', 'png', 'pdf', 'txt', 'log', 'zip',
                    'mp4', 'gif'
                ]
            )
        ],
    )
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['uploaded_at']),
        ]
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_name}"

    def save(self, *args, **kwargs):
        if not self.original_name:
            self.original_name = self.file.name.split('/')[-1]
        if not self.size and self.file:
            self.size = self.file.size
        if not self.mime_type and self.file:
            self.mime_type, _ = mimetypes.guess_type(self.file.name)
            self.mime_type = self.mime_type or 'application/octet-stream'
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.file and default_storage.exists(self.file.path):
            default_storage.delete(self.file.path)
        super().delete(*args, **kwargs)
