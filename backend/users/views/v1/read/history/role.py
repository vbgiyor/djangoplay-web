from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import Role
from users.serializers.v1.read import RoleReadSerializerV1


@extend_schema(tags=["Users: Role"])
class RoleHistoryAPIView(BaseHistoryListAPIView):
    queryset = Role.objects.all()
    history_queryset = Role.history.all()
    serializer_class = RoleReadSerializerV1
