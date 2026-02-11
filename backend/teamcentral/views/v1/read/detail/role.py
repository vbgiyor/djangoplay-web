from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import Role
from teamcentral.serializers.v1.read import RoleReadSerializerV1


@extend_schema(tags=["Teamcentral: Role"])
class RoleDetailAPIView(RetrieveAPIView):
    queryset = Role.objects.filter(deleted_at__isnull=True)
    serializer_class = RoleReadSerializerV1
