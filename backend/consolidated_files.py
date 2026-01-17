# Files included: ['audit/constants.py', 'audit/__init__.py', 'audit/apps.py', 'audit/admin.py', 'audit/exceptions.py', 'audit/tests.py', 'audit/views.py', 'audit/middleware/api_audit.py', 'audit/middleware/__init__.py', 'audit/contracts/__init__.py', 'audit/contracts/target.py', 'audit/contracts/actor.py', 'audit/signals/events.py', 'audit/signals/__init__.py', 'audit/signals/lifecycle.py', 'audit/models/__init__.py', 'audit/models/audit_event.py', 'audit/services/recorder.py', 'audit/services/__init__.py', 'audit/services/normalizer.py']

#audit/constants.py
from django.conf import settings

AUDIT_ADMIN_ROLES = getattr(
    settings,
    "AUDIT_ADMIN_ROLES",
    {"DJGO", "CEO", "CFO", "SSO"},
)
####################################################################################
#audit/__init__.py

####################################################################################
#audit/apps.py
from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"

    def ready(self):
        """
        Register audit lifecycle signal handlers.

        Important:
        - Import happens here to avoid early model loading
        - Signals are observational only
        - No domain logic is executed at import time

        """
        from audit.signals import lifecycle  # noqa: F401
####################################################################################
#audit/admin.py
from audit.constants import AUDIT_ADMIN_ROLES
from audit.models.audit_event import AuditEvent
from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.contrib.admin import display
from django.utils.translation import gettext_lazy as _
from policyengine.commons.base import get_user_role


@AdminIconDecorator.register_with_icon(AuditEvent)
class AuditEventAdmin(BaseAdmin):

    # ------------------------------------------------------------------
    # LIST VIEW
    # ------------------------------------------------------------------
    list_display = (
        "occurred_at",
        "action",
        "actor_display",
        "target_display",
        "client_ip",
        "is_system_event",
    )

    list_filter = (
        "action",
        "actor_type",
        "target_type",
        "is_system_event",
    )

    search_fields = (
        "actor_label",
        "target_label",
        "request_id",
    )

    ordering = ("-occurred_at",)
    list_per_page = 50
    date_hierarchy = "occurred_at"

    # ------------------------------------------------------------------
    # DETAIL VIEW (READ-ONLY)
    # ------------------------------------------------------------------
    readonly_fields = (
        "occurred_at",
        "action",
        "actor_type",
        "actor_id",
        "actor_label",
        "target_type",
        "target_id",
        "target_label",
        "client_ip",
        "request_id",
        "user_agent",
        "is_system_event",
        "metadata",
    )

    fieldsets = (
        (_("Event"), {
            "fields": (
                "occurred_at",
                "action",
                "is_system_event",
            )
        }),
        (_("Actor"), {
            "fields": (
                "actor_type",
                "actor_id",
                "actor_label",
            )
        }),
        (_("Target"), {
            "fields": (
                "target_type",
                "target_id",
                "target_label",
            )
        }),
        (_("Request Context"), {
            "fields": (
                "client_ip",
                "request_id",
                "user_agent",
            )
        }),
        (_("Metadata"), {
            "fields": ("metadata",),
        }),
    )

    # ------------------------------------------------------------------
    # HARD PERMISSION RULES
    # ------------------------------------------------------------------
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ------------------------------------------------------------------
    # ROLE-BASED VISIBILITY
    # ------------------------------------------------------------------
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        role = get_user_role(request.user)
        return role in AUDIT_ADMIN_ROLES

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        role = get_user_role(request.user)
        if role not in AUDIT_ADMIN_ROLES:
            return qs.none()

        return qs


    # ------------------------------------------------------------------
    # DISPLAY HELPERS
    # ------------------------------------------------------------------
    @display(description="Actor")
    def actor_display(self, obj):
        if obj.actor_label:
            return f"{obj.actor_label} ({obj.actor_type})"
        return "-"

    @display(description="Target")
    def target_display(self, obj):
        if obj.target_label:
            return f"{obj.target_label} ({obj.target_type})"
        return "-"
####################################################################################
#audit/exceptions.py

####################################################################################
#audit/tests.py
# Create your tests here.
####################################################################################
#audit/views.py
from django.shortcuts import render
from django.test import TestCase

# Create your views here.
####################################################################################
#audit/middleware/api_audit.py
"""
Audit context enrichment middleware.

Responsibilities:
- Attach best-effort actor information to request
- Ensure request context is available to audit recorder
- Never raise
- Never block request
"""

import logging

from audit.contracts.actor import AuditActor

logger = logging.getLogger(__name__)


class APIAuditMiddleware:

    """
    Enrich request with audit actor context.

    This middleware:
    - Does NOT record audit events
    - Does NOT enforce authentication
    - Does NOT raise
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            user = getattr(request, "user", None)

            if user and getattr(user, "is_authenticated", False):
                request.audit_actor = AuditActor(
                    id=user.pk,
                    type="user",
                    label=getattr(user, "email", None),
                )
            else:
                request.audit_actor = None

        except Exception:
            logger.exception("APIAuditMiddleware failed to attach actor")

        return self.get_response(request)
####################################################################################
#audit/middleware/__init__.py

####################################################################################
#audit/contracts/__init__.py

####################################################################################
#audit/contracts/target.py
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuditTarget:

    """
    Represents the target of an audited action.

    This is a contract object — NOT a Django model.

    Examples:
        - support_ticket
        - invoice
        - client
        - location
        - authentication_session

    """

    type: str
    id: Optional[int]
    label: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "id": self.id,
            "label": self.label,
        }
####################################################################################
#audit/contracts/actor.py
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuditActor:

    """
    Represents the actor responsible for an audited action.

    This is a contract object — NOT a Django model.

    Examples:
        - Authenticated user
        - Anonymous user
        - System / background job
        - External service

    The audit system never assumes ORM availability.

    """

    id: Optional[int]
    type: str
    label: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
        }
####################################################################################
#audit/signals/events.py
from django.dispatch import Signal

# Fired AFTER a model is soft-deleted
post_soft_delete = Signal()

# Fired AFTER a model is restored
post_restore = Signal()
####################################################################################
#audit/signals/__init__.py

####################################################################################
#audit/signals/lifecycle.py
import logging

from audit.contracts.actor import AuditActor
from audit.contracts.target import AuditTarget
from audit.services.recorder import AuditRecorder
from audit.signals.events import post_restore, post_soft_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# SOFT DELETE SIGNAL
# ---------------------------------------------------------------------
@receiver(post_soft_delete)
def audit_post_soft_delete(sender, instance, **kwargs):
    """
    Record audit event AFTER a model is soft-deleted.

    This handler:
    - Observes only
    - Never mutates domain models
    - Never raises
    """
    try:
        _record_lifecycle_event(
            action="deleted",
            instance=instance,
        )
    except Exception:
        logger.exception(
            "audit_post_soft_delete failed",
            extra={
                "model": sender.__name__,
                "pk": getattr(instance, "pk", None),
            },
        )


# ---------------------------------------------------------------------
# RESTORE SIGNAL
# ---------------------------------------------------------------------
@receiver(post_restore)
def audit_post_restore(sender, instance, **kwargs):
    """
    Record audit event AFTER a model is restored.

    This handler:
    - Observes only
    - Never mutates domain models
    - Never raises
    """
    try:
        _record_lifecycle_event(
            action="restored",
            instance=instance,
        )
    except Exception:
        logger.exception(
            "audit_post_restore failed",
            extra={
                "model": sender.__name__,
                "pk": getattr(instance, "pk", None),
            },
        )


# ---------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------
def _record_lifecycle_event(*, action: str, instance):
    """
    Record a lifecycle audit event using canonical contracts.
    """
    # -------------------------------
    # ACTOR
    # -------------------------------
    actor = None
    deleted_by = getattr(instance, "deleted_by", None)

    if deleted_by:
        actor = AuditActor(
            id=getattr(deleted_by, "pk", None),
            type="user",
            label=getattr(deleted_by, "email", None),
        )

    # -------------------------------
    # TARGET
    # -------------------------------
    target = AuditTarget(
        type=f"{instance._meta.app_label}.{instance.__class__.__name__}",
        id=instance.pk,
        label=str(instance),
    )

    # -------------------------------
    # RECORD
    # -------------------------------
    AuditRecorder.record(
        action=action,
        actor=actor,
        target=target,
        metadata={
            "model": instance.__class__.__name__,
            "app": instance._meta.app_label,
        },
        is_system_event=actor is None,
    )
####################################################################################
#audit/models/__init__.py
from .audit_event import AuditEvent

__all__ = ["AuditEvent"]
####################################################################################
#audit/models/audit_event.py
from django.db import models
from django.utils import timezone


class AuditEvent(models.Model):

    """
    Immutable audit log entry.

    This model is intentionally:
    - Append-only
    - Denormalized
    - Free of foreign keys to domain models

    It represents a factual record of something that already happened.
    """

    # ------------------------------------------------------------------
    # Core identity
    # ------------------------------------------------------------------
    id = models.BigAutoField(primary_key=True)

    occurred_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the audited action occurred."
    )

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------
    action = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Canonical action name (e.g. create, update, delete, login)."
    )

    # ------------------------------------------------------------------
    # Actor (who)
    # ------------------------------------------------------------------
    actor_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Identifier of the actor (user id, service id, etc.)."
    )

    actor_type = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Type of actor (user, system, service)."
    )

    actor_label = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Human-readable actor identifier (email, username)."
    )

    # ------------------------------------------------------------------
    # Target (what)
    # ------------------------------------------------------------------
    target_type = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Type of entity affected (invoice, client, member, etc.)."
    )

    target_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Identifier of the affected entity."
    )

    target_label = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Human-readable target identifier."
    )

    # ------------------------------------------------------------------
    # Request / execution context
    # ------------------------------------------------------------------
    request_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Request ID for correlating distributed actions."
    )

    client_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address, if available."
    )

    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="User agent string, if available."
    )

    # ------------------------------------------------------------------
    # Extra data
    # ------------------------------------------------------------------
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary structured metadata relevant to the event."
    )

    # ------------------------------------------------------------------
    # System flags
    # ------------------------------------------------------------------
    is_system_event = models.BooleanField(
        default=False,
        help_text="True if generated by system/middleware rather than a user."
    )

    class Meta:
        db_table = "audit_event"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["action", "occurred_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

        managed = True

    def __str__(self) -> str:
        return f"[{self.occurred_at}] {self.action} ({self.target_type}:{self.target_id})"
####################################################################################
#audit/services/recorder.py
import logging
from typing import Any, Dict, Optional

from audit.models.audit_event import AuditEvent
from audit.services.normalizer import normalize_actor, normalize_target
from core.request_context import client_ip, request_id
from django.utils import timezone

logger = logging.getLogger(__name__)


class AuditRecorder:

    """
    Central audit write service.

    Design guarantees:
    - Never raises
    - Never blocks business logic
    - Never imports domain models
    - Safe for sync, async, and background execution
    """

    @staticmethod
    def record(
        *,
        action: str,
        actor=None,
        target=None,
        metadata: Optional[Dict[str, Any]] = None,
        is_system_event: bool = False,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Record an immutable audit event.
        """
        if not action:
            logger.warning("AuditRecorder.record called without action")
            return

        try:
            actor_data = normalize_actor(actor)
            target_data = normalize_target(target)

            AuditEvent.objects.create(
                occurred_at=timezone.now(),
                action=action,
                request_id=request_id.get(),
                client_ip=client_ip.get(),
                user_agent=user_agent,
                is_system_event=is_system_event,
                metadata=metadata or {},
                **actor_data,
                **target_data,
            )
            logger.info(
                "Audit event recorded",
                extra={
                    "action": action,
                    "actor": actor_data,
                    "target": target_data,
                    "request_id": request_id.get(),
                },
            )

        except Exception as exc:
            # ABSOLUTE RULE: auditing must never break runtime
            logger.error(
                "AuditRecorder failed (action=%s)",
                action,
                exc_info=exc,
            )
####################################################################################
#audit/services/__init__.py
from .recorder import AuditRecorder

__all__ = ["AuditRecorder"]
####################################################################################
#audit/services/normalizer.py
from typing import Any, Dict, Optional

from audit.contracts.actor import AuditActor
from audit.contracts.target import AuditTarget


def normalize_actor(actor: Optional[AuditActor]) -> Dict[str, Optional[str]]:
    if not actor:
        return {
            "actor_id": None,
            "actor_type": None,
            "actor_label": None,
        }

    return {
        "actor_id": str(actor.id) if actor.id is not None else None,
        "actor_type": actor.type,
        "actor_label": actor.label,
    }


def normalize_target(target: Optional[AuditTarget]) -> Dict[str, Optional[str]]:
    if not target:
        return {
            "target_type": None,
            "target_id": None,
            "target_label": None,
        }

    return {
        "target_type": target.type,
        "target_id": str(target.id) if target.id is not None else None,
        "target_label": target.label,
    }
####################################################################################
