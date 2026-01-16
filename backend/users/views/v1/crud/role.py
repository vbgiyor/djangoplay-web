from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import Role
from users.serializers.v1.read import RoleReadSerializerV1
from users.serializers.v1.write import RoleWriteSerializerV1


@extend_schema(tags=["Users: Role"])
class RoleViewSet(BaseViewSet):
    queryset = Role.objects.filter(deleted_at__isnull=True)

    read_serializer_class = RoleReadSerializerV1
    write_serializer_class = RoleWriteSerializerV1
