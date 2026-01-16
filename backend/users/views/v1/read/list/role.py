from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import Role
from users.serializers.v1.read import RoleReadSerializerV1


@extend_schema(tags=["Users: Role"])
class RoleListAPIView(BaseListAPIView):
    queryset = Role.objects.filter(deleted_at__isnull=True)
    serializer_class = RoleReadSerializerV1
