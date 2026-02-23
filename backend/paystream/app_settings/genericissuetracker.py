from django.conf import settings as django_settings

GENERIC_ISSUETRACKER_DEFAULT_PERMISSION_CLASSES = [
    "rest_framework.permissions.IsAuthenticated"
    # "rest_framework.permissions.AllowAny"
]
GENERIC_ISSUETRACKER_PAGE_SIZE = 10

GENERIC_ISSUETRACKER_ALLOW_ANONYMOUS_REPORTING = True

GENERIC_ISSUETRACKER_IDENTITY_RESOLVER = \
    "users.services.issuetracker_identity_resolver.DjangoPlayIssueTrackerIdentityResolver"

# --------------------------------------------------------------
# Issue Status Transition Policy
# --------------------------------------------------------------
TRANSITION_POLICY = "paystream.integrations.issuetracker.access-control.permissions.IssueStateTransitionOwnerPolicy"

# --------------------------------------------------------------
# Issue Internal Visibility (RBAC)
# --------------------------------------------------------------
ISSUE_INTERNAL_ALLOWED_ROLES = [
    "CEO",
    "DJGO",
    "SSO",
]