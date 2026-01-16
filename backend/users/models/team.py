import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from .department import Department
from .employee import Employee

logger = logging.getLogger(__name__)

class Team(TimeStampedModel, AuditFieldsModel):

    """Model for organizational teams."""

    name = models.CharField(max_length=100, help_text="Team name")
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='teams',
        help_text='Team department'
    )
    leader = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_teams',
        help_text='Team leader'
    )
    description = models.TextField(blank=True, help_text='Team description')
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Teams"
        indexes = [
            models.Index(fields=['department', 'name'], name='team_dept_name_idx'),
            models.Index(fields=['leader'], name='team_leader_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['name', 'department'], name='unique_team_name_per_dept')
        ]

    def __str__(self):
        return f"{self.name} ({self.department.code})"

    def clean(self):
        """Validate team fields."""
        logger.debug(f"Cleaning Team: name={self.name}")
        if not self.name or not self.department:
            raise ValueError("Name and department are required.")
        if self.leader and self.leader.department != self.department:
            raise ValueError("Leader must be in the same department.")
        super().clean()

    def save(self, *args, user=None, **kwargs):
        """Save with audit fields."""
        self.clean()
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"Team saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete team and reassign members."""
        logger.info(f"Soft deleting Team: {self.name}, user={user}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.is_active = False
        self.members.update(team=None)  # Reassign members to no team
        self.save(user=user)
