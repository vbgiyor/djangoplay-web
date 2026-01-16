from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import UserActivityLog
from users.serializers.v1.read import UserActivityLogReadSerializerV1


@extend_schema(tags=["Users: Activity Log"])
class UserActivityLogListAPIView(BaseListAPIView):
    queryset = UserActivityLog.objects.filter(deleted_at__isnull=True)
    serializer_class = UserActivityLogReadSerializerV1
