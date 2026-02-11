from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from teamcentral.models import Role
from teamcentral.serializers.v1.read import RoleReadSerializerV1


@extend_schema(tags=["Teamcentral: Role"])
class RoleListAPIView(BaseListAPIView):
    queryset = Role.objects.filter(deleted_at__isnull=True)
    serializer_class = RoleReadSerializerV1
