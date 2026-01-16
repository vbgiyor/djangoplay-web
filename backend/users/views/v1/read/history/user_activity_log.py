from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import UserActivityLog
from users.serializers.v1.read import UserActivityLogReadSerializerV1


@extend_schema(tags=["Users: Activity Log"])
class UserActivityLogHistoryAPIView(BaseHistoryListAPIView):
    queryset = UserActivityLog.objects.all()
    history_queryset = UserActivityLog.history.all()
    serializer_class = UserActivityLogReadSerializerV1
