from django.conf import settings
from django.db import models


class FeatureFlag(models.Model):

    """
    A feature flag that can be enabled globally, per role, per user, etc.
    """

    key = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    enabled_globally = models.BooleanField(default=False)
    # Optionally scope by roles or users
    roles = models.JSONField(default=list, blank=True)  # e.g. ["CEO", "CFO"]
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)

    class Meta:
        ordering = ["key"]

    def is_enabled_for(self, user):
        if self.enabled_globally:
            return True
        # user-specific override
        if self.users.filter(pk=user.pk).exists():
            return True
        # role-based
        from policyengine.commons.base import get_user_role
        role = get_user_role(user)
        if role and role in self.roles:
            return True
        return False
