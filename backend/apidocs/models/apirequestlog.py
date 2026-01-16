from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()

class APIRequestLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    response_status = models.IntegerField()
    timestamp = models.DateTimeField(default=timezone.now)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    is_public_api = models.BooleanField(
        default=False,
        help_text="Is this endpoint publicly documented and exposed?"
    )

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.method} {self.path} - {self.response_status}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            from django.urls import resolve
            from rest_framework.permissions import AllowAny, IsAuthenticated

            try:
                match = resolve(self.path)
                view = match.func

                # For DRF viewsets, underlying class is on .cls
                view_cls = getattr(view, "cls", None)
                if view_cls is not None and hasattr(view_cls, "permission_classes"):
                    permission_classes = list(view_cls.permission_classes or [])
                else:
                    permission_classes = list(getattr(view, "permission_classes", []) or [])

                if not permission_classes:
                    # No explicit permission → treat as private by default
                    self.is_public_api = False
                elif AllowAny in permission_classes:
                    self.is_public_api = True
                elif IsAuthenticated in permission_classes:
                    self.is_public_api = False
                else:
                    # Conservative: private unless explicitly AllowAny
                    self.is_public_api = False

            except Exception:
                self.is_public_api = False

        super().save(*args, **kwargs)
