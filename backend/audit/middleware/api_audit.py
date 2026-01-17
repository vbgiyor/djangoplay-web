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
