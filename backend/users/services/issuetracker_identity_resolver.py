from genericissuetracker.services.identity import DefaultIdentityResolver

from users.services.identity_query_service import IdentityQueryService


class DjangoPlayIssueTrackerIdentityResolver(DefaultIdentityResolver):

    """
    Identity adapter between DjangoPlay and GenericIssueTracker.

    Responsibilities:
    - Extract authenticated user from request
    - Return deterministic identity contract
    - Remain read-only
    """

    def resolve(self, request):
        user = request.user

        if not user or not user.is_authenticated:
            return {
                "id": None,
                "email": None,
                "is_authenticated": False,
            }

        # Optionally use snapshot service
        snapshot = IdentityQueryService.get_identity_snapshot(user.id)

        return {
            "id": snapshot["id"],
            "email": snapshot["email"],
            "is_authenticated": True,
            "is_superuser": user.is_superuser,
            "role_code": getattr(getattr(user, "role", None), "code", None),
        }
