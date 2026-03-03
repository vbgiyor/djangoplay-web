GENERIC_ISSUETRACKER_PAGE_SIZE = 10

GENERIC_ISSUETRACKER_ALLOW_ANONYMOUS_REPORTING = True

GENERIC_ISSUETRACKER_IDENTITY_RESOLVER = \
    "users.services.issuetracker_identity_resolver.DjangoPlayIssueTrackerIdentityResolver"

GENERIC_ISSUETRACKER_DEFAULT_PERMISSION_CLASSES = [
    "paystream.integrations.issuetracker.access-control.permissions.IssueTrackerAccessPermission"
]

# --------------------------------------------------------------
# Issue Status Transition Policy
# --------------------------------------------------------------
GENERIC_ISSUETRACKER_TRANSITION_POLICY = "paystream.integrations.issuetracker.access-control.permissions.IssueStateTransitionOwnerPolicy"

# --------------------------------------------------------------
# Issue Internal Visibility (RBAC)
# --------------------------------------------------------------
GENERIC_ISSUETRACKER_ISSUE_INTERNAL_ALLOWED_ROLES = [
    "CEO",
    "DJGO",
    "SSO",
]

# --------------------------------------------------------------
# Comment Controls
# --------------------------------------------------------------
# Hard limit enforced in:
#   - API serializer
#   - UI mutation service
#   - Database layer (TextField max_length=10000)
#
# Keep ≤ 10000 (database hard cap)
# --------------------------------------------------------------
GENERIC_ISSUETRACKER_MAX_COMMENT_LENGTH = 5000
