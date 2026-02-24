"""
Issue Tracker Integration View Layer
=====================================

This module exposes DjangoPlay-integrated ViewSets that extend
GenericIssueTracker core ViewSets.

Purpose
-------
- Emit integration signals
- Preserve schema determinism
- Avoid modifying third-party package
- Maintain upgrade safety
"""

from .v1.crud.attachment import IntegratedAttachmentCRUDViewSet
from .v1.crud.comment import IntegratedCommentCRUDViewSet
from .v1.crud.issue import IntegratedIssueCRUDViewSet

__all__ = [
    "IntegratedIssueCRUDViewSet",
    "IntegratedCommentCRUDViewSet",
    "IntegratedAttachmentCRUDViewSet",
]
