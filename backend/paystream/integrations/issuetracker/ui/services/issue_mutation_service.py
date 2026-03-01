from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied

from genericissuetracker.models import IssueComment
from genericissuetracker.services.identity import get_identity_resolver
from genericissuetracker.services.issue_lifecycle import change_issue_status
from genericissuetracker.signals import issue_commented


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


# ------------------------------------------------------------------
# Mutation Service
# ------------------------------------------------------------------

class IssueMutationService:
    """
    UI-level mutation orchestration.

    Responsibilities:
        - Resolve identity via canonical resolver
        - Enforce anonymous comment policy
        - Delegate lifecycle to domain engine
        - Emit comment signal
        - Never duplicate lifecycle logic
        - Never duplicate policy logic
    """

    # ---------------------------------------------------------
    # Add Comment
    # ---------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def add_comment(*, issue, request, body: str, commenter_email: str | None) -> CommentResult:

        body = (body or "").strip()
        if not body:
            return CommentResult(False, "Comment body cannot be empty.")

        allow_anonymous = getattr(
            settings,
            "GENERIC_ISSUETRACKER_ALLOW_ANONYMOUS_REPORTING",
            False,
        )

        resolver = get_identity_resolver()
        identity = resolver.resolve(request) or {}

        is_authenticated = identity.get("is_authenticated", False)
        resolved_email = identity.get("email")

        # -----------------------------------------------------
        # Authenticated path
        # -----------------------------------------------------
        if is_authenticated:
            if not resolved_email:
                return CommentResult(False, "Authenticated user has no email.")

            email = resolved_email

        # -----------------------------------------------------
        # Anonymous path
        # -----------------------------------------------------
        else:
            if not allow_anonymous:
                return CommentResult(False, "Anonymous comments not allowed.")

            # SAFETY: anonymous cannot comment on internal issues
            if not issue.is_public:
                return CommentResult(False, "Cannot comment on internal issue.")

            if not commenter_email:
                return CommentResult(False, "Email required.")

            email = commenter_email.strip().lower()

        # -----------------------------------------------------
        # Create comment
        # -----------------------------------------------------
        comment = IssueComment.objects.create(
            issue=issue,
            body=body,
            commenter_email=email,
            commenter_user_id=identity.get("id"),
        )

        # -----------------------------------------------------
        # Emit domain signal
        # -----------------------------------------------------
        issue_commented.send(
            sender=issue.__class__,
            issue=issue,
            comment=comment,
            identity=identity,
            request=request,
        )

        return CommentResult(True)

    # ---------------------------------------------------------
    # Change Status
    # ---------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def change_status(*, issue, request, new_status: str) -> StatusChangeResult:

        resolver = get_identity_resolver()
        identity = resolver.resolve(request) or {}

        if not identity.get("is_authenticated"):
            return StatusChangeResult(False, "Authentication required.")

        try:
            # FULL lifecycle enforcement
            change_issue_status(issue, new_status, identity)

        except ValidationError as exc:
            return StatusChangeResult(False, str(exc.detail))

        except PermissionDenied as exc:
            return StatusChangeResult(False, str(exc.detail))

        except Exception as exc:
            return StatusChangeResult(False, str(exc))

        return StatusChangeResult(True)
    