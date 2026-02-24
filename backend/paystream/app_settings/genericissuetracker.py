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
TRANSITION_POLICY = "paystream.integrations.issuetracker.access-control.permissions.IssueStateTransitionOwnerPolicy"

# --------------------------------------------------------------
# Issue Internal Visibility (RBAC)
# --------------------------------------------------------------
ISSUE_INTERNAL_ALLOWED_ROLES = [
    "CEO",
    "DJGO",
    "SSO",
]
