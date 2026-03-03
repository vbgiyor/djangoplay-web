"""
Protected Attachment Download View
===================================

Enterprise-grade secure file streaming.

Enforces:
- RBAC visibility
- 404 masking
- Identity resolution
- Access logging
"""

import logging
import os

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from genericissuetracker.models import IssueAttachment
from genericissuetracker.services.identity import get_identity_resolver
from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)

logger = logging.getLogger(__name__)


def protected_attachment_download(request, number: int):
    """
    Secure attachment streaming endpoint.
    """
    attachment = get_object_or_404(
        IssueAttachment.objects.select_related("issue"),
        number=number,
    )

    identity = get_identity_resolver().resolve(request)
    visibility = IssueVisibilityService(identity)

    # RBAC visibility enforcement
    visible = visibility.filter_attachment_queryset(
        IssueAttachment.objects.filter(pk=attachment.pk)
    ).exists()

    if not visible:
        raise Http404("File not found")

    file_path = attachment.file.path

    if not os.path.exists(file_path):
        raise Http404("File not found")

    logger.info(
        "[IssueAttachmentDownload] attachment_id=%s issue_number=%s identity=%s",
        attachment.id,
        attachment.issue.issue_number,
        identity,
    )

    response = FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=attachment.original_name,
    )

    return response
