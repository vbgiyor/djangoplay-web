from genericissuetracker.services.identity import get_identity_resolver
from genericissuetracker.views.v1.read.comment import (
    CommentReadViewSet as BaseCommentReadViewSet,
)
from paystream.integrations.issuetracker.services.visibility import (
    IssueVisibilityService,
)


class IntegratedCommentReadViewSet(BaseCommentReadViewSet):

    def get_queryset(self):
        queryset = super().get_queryset()
        identity = get_identity_resolver().resolve(self.request)
        visibility = IssueVisibilityService(identity)
        return visibility.filter_comment_queryset(queryset)
