from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import UserActivityLog
from users.serializers.v1.read import UserActivityLogReadSerializerV1


@extend_schema(tags=["Users: Activity Log"])
class UserActivityLogDetailAPIView(RetrieveAPIView):
    queryset = UserActivityLog.objects.filter(deleted_at__isnull=True)
    serializer_class = UserActivityLogReadSerializerV1
