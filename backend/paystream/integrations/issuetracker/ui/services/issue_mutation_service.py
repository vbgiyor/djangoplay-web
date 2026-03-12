from collections.abc import Iterable
from dataclasses import dataclass

from django.db import transaction
from django.http import QueryDict
from genericissuetracker.models import IssueAttachment, IssueComment, Label
from genericissuetracker.serializers.v1.write.attachment import (
    IssueAttachmentUploadSerializer,
)
from genericissuetracker.serializers.v1.write.issue import IssueCreateSerializer
from genericissuetracker.services.identity import get_identity_resolver
from genericissuetracker.services.issue_lifecycle import change_issue_status
from genericissuetracker.settings import get_setting
from genericissuetracker.signals import (
    attachment_added,
    issue_commented,
)
from paystream.integrations.issuetracker.constants import IssueLabelSlug
from paystream.integrations.issuetracker.services.label_bootstrap import (
    IssueLabelBootstrapService,
)
from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)
from rest_framework.exceptions import PermissionDenied, ValidationError

# ------------------------------------------------------------------
# Result Objects
# ------------------------------------------------------------------

@dataclass(frozen=True)
class CommentResult:
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class StatusChangeResult:
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class AttachmentResult:
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class IssueCreateResult:
    success: bool
    issue: object | None = None
    error: str | None = None


# ------------------------------------------------------------------
# Mutation Service
# ------------------------------------------------------------------

class IssueMutationService:

    """
    UI-level mutation orchestration.

    Responsibilities:
        - Resolve identity via canonical resolver
        - Enforce anonymous policy
        - Delegate lifecycle to domain engine
        - Reuse library serializers for validation
        - Never duplicate lifecycle logic
        - Never duplicate policy logic
    """

    # ---------------------------------------------------------
    # Create Issue (delegates to library serializer)
    # ---------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def create_issue(*, request, data=None, files=None) -> IssueCreateResult:

        resolver = get_identity_resolver()
        identity = resolver.resolve(request) or {}

        allow_anonymous = get_setting("ALLOW_ANONYMOUS_REPORTING")

        is_authenticated = identity.get("is_authenticated", False)

        # Initialize payload first
        if data is None:
            data = request.POST.copy()

        # Anonymous creation governance
        if not is_authenticated and not allow_anonymous:
            return IssueCreateResult(
                False,
                None,
                "Authentication required to create issue.",
            )

        # Internal issue RBAC enforcement. (payload already contains is_public)
        is_public = data.get("is_public") in (True, "on", "true", "True", "1")

        if not is_public:

            if not is_authenticated:
                return IssueCreateResult(
                    False,
                    None,
                    "Internal issues require authentication.",
                )
            visibility = IssueVisibilityService(identity)

            if not visibility.can_access_internal():
                return IssueCreateResult(
                    False,
                    None,
                    "You are not allowed to create internal issues.",
                )

        # attach files as a list
        if files is None:
            files = request.FILES.getlist("files")

        # If caller passed plain dict (service integrations)
        if isinstance(data, dict):
            q = QueryDict("", mutable=True)
            for k, v in data.items():
                if isinstance(v, list):
                    q.setlist(k, v)
                else:
                    q[k] = v
            data = q

        # ---------------------------------------------------------
        # Attach files
        # ---------------------------------------------------------
        if files:
            data.setlist("files", files)
        else:
            data.pop("files", None)

        serializer = IssueCreateSerializer(
            data=data,
            context={"request": request}
        )

        try:
            serializer.is_valid(raise_exception=True)
            issue = serializer.save()

        except ValidationError as exc:
            return IssueCreateResult(False, None, str(exc))

        except Exception as exc:
            return IssueCreateResult(False, None, str(exc))

        # Assign bug visibility labels (non-critical)
        try:

            # IssueLabelBootstrapService.ensure_labels_exist()

            if issue.is_public:
                label_slug = IssueLabelSlug.BUG_PUBLIC
            else:
                label_slug = IssueLabelSlug.BUG_INTERNAL

            from genericissuetracker.models import Label

            label = Label.objects.get(slug=label_slug)

            if label:
                issue.labels.add(label)

        except Exception:
            # label assignment should never break issue creation
            pass

        return IssueCreateResult(True, issue)

    def _parse_checkbox(value):
        return value in (True, "on", "true", "True", "1")

    # ---------------------------------------------------------
    # Add Comment
    # ---------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def add_comment(
        *,
        issue,
        request,
        body: str | None,
        commenter_email: str | None,
        files: Iterable | None = None,
    ) -> CommentResult:

        files = files or []
        body = (body or "").strip()

        if not body and not files:
            return CommentResult(False, "Comment or attachment required.")

        max_length = get_setting("MAX_COMMENT_LENGTH")

        if body and len(body) > max_length:
            return CommentResult(
                False,
                f"Comment cannot exceed {max_length} characters."
            )

        allow_anonymous = get_setting("ALLOW_ANONYMOUS_REPORTING")

        resolver = get_identity_resolver()
        identity = resolver.resolve(request) or {}

        is_authenticated = identity.get("is_authenticated", False)
        resolved_email = identity.get("email")

        # Authenticated
        if is_authenticated:
            if not resolved_email:
                return CommentResult(False, "Authenticated user has no email.")
            email = resolved_email

        # Anonymous
        else:
            if not allow_anonymous:
                return CommentResult(False, "Anonymous comments not allowed.")

            if not issue.is_public:
                return CommentResult(False, "Cannot comment on internal issue.")

            if not commenter_email:
                return CommentResult(False, "Email required.")

            email = commenter_email.strip().lower()

        comment = None

        if body:
            comment = IssueComment.objects.create(
                issue=issue,
                body=body,
                commenter_email=email,
                commenter_user_id=identity.get("id"),
            )

            issue_commented.send(
                sender=issue.__class__,
                issue=issue,
                comment=comment,
                identity=identity,
            )

        for f in files:
            attachment = IssueAttachment.objects.create(
                issue=issue,
                comment=comment,
                file=f,
                uploaded_by_email=email,
                uploaded_by_user_id=identity.get("id"),
            )

            attachment_added.send(
                sender=attachment.__class__,
                issue=issue,
                attachment=attachment,
                identity=identity,
                comment=comment,
            )

        return CommentResult(True)

    # ---------------------------------------------------------
    # Change Status (delegates to lifecycle)
    # ---------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def change_status(*, issue, request, new_status: str) -> StatusChangeResult:

        resolver = get_identity_resolver()
        identity = resolver.resolve(request) or {}

        if not identity.get("is_authenticated"):
            return StatusChangeResult(False, "Authentication required.")

        try:
            change_issue_status(issue, new_status, identity)
        except (ValidationError, PermissionDenied) as exc:
            return StatusChangeResult(False, str(exc))
        except Exception as exc:
            return StatusChangeResult(False, str(exc))

        return StatusChangeResult(True)

    # ---------------------------------------------------------
    # Add Attachments (delegates to library serializer)
    # ---------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def add_attachments(*, issue, request, files: Iterable) -> AttachmentResult:

        if not files:
            return AttachmentResult(False, "No files provided.")

        resolver = get_identity_resolver()
        identity = resolver.resolve(request) or {}

        if not identity.get("is_authenticated") and not issue.is_public:
            return AttachmentResult(
                False,
                "Cannot attach files to internal issue."
            )

        for f in files:
            serializer = IssueAttachmentUploadSerializer(
                data={
                    "issue": issue.issue_number,
                    "file": f,
                },
                context={"request": request},
            )

            try:
                serializer.is_valid(raise_exception=True)
                serializer.save()
            except ValidationError as exc:
                return AttachmentResult(False, str(exc))
            except Exception as exc:
                return AttachmentResult(False, str(exc))

        return AttachmentResult(True)

