"""
Integrated Attachment ViewSet
=============================

- Enforces RBAC visibility governance
- Uses secure serializer override
- Emits audit events
"""

from audit.contracts.actor import AuditActor
from audit.contracts.target import AuditTarget
from audit.services.recorder import AuditRecorder
from django.db import transaction
from genericissuetracker.services.identity import get_identity_resolver
from genericissuetracker.views.v1.crud.attachment import (
    AttachmentCRUDViewSet,
)
from paystream.integrations.issuetracker.serializers.v1.read.attachment import (
    IntegratedAttachmentReadSerializer,
)
from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)


class IntegratedAttachmentCRUDViewSet(AttachmentCRUDViewSet):

    read_serializer_class = IntegratedAttachmentReadSerializer

    # ----------------------------------------------------------
    # Visibility Governance
    # ----------------------------------------------------------
    def get_queryset(self):
        queryset = super().get_queryset()

        identity = get_identity_resolver().resolve(self.request)
        visibility = IssueVisibilityService(identity)

        return visibility.filter_attachment_queryset(queryset)

    # ----------------------------------------------------------
    # Audit: Attachment Uploaded
    # ----------------------------------------------------------
    def perform_create(self, serializer):
        identity = get_identity_resolver().resolve(self.request)

        with transaction.atomic():
            attachment = serializer.save()

            actor = None
            if identity.get("is_authenticated"):
                actor = AuditActor(
                    id=identity.get("id"),
                    type="user",
                    label=identity.get("email"),
                )

            target = AuditTarget(
                type="issuetracker.Attachment",
                id=str(attachment.id),
                label=attachment.original_name,
            )

            metadata = {
                "issue_number": attachment.issue.issue_number,
                "attachment_id": str(attachment.id),
                "original_name": attachment.original_name,
                "size": attachment.size,
                "is_public": attachment.issue.is_public,
            }

            AuditRecorder.record(
                action="attachment_uploaded",
                actor=actor,
                target=target,
                metadata=metadata,
                is_system_event=actor is None,
            )

    # ----------------------------------------------------------
    # Audit: Attachment Deleted
    # ----------------------------------------------------------
    def perform_destroy(self, instance):
        identity = get_identity_resolver().resolve(self.request)

        actor = None
        if identity.get("is_authenticated"):
            actor = AuditActor(
                id=identity.get("id"),
                type="user",
                label=identity.get("email"),
            )

        target = AuditTarget(
            type="issuetracker.Attachment",
            id=str(instance.id),
            label=instance.original_name,
        )

        metadata = {
            "issue_number": instance.issue.issue_number,
            "attachment_id": str(instance.id),
            "original_name": instance.original_name,
            "is_public": instance.issue.is_public,
        }

        AuditRecorder.record(
            action="attachment_deleted",
            actor=actor,
            target=target,
            metadata=metadata,
            is_system_event=actor is None,
        )

        super().perform_destroy(instance)
