from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import EmploymentStatus
from users.serializers.v1.read import EmploymentStatusReadSerializerV1
from users.serializers.v1.write import EmploymentStatusWriteSerializerV1


@extend_schema(tags=["Users: Employment Status"])
class EmploymentStatusViewSet(BaseViewSet):
    queryset = EmploymentStatus.objects.filter(deleted_at__isnull=True)

    read_serializer_class = EmploymentStatusReadSerializerV1
    write_serializer_class = EmploymentStatusWriteSerializerV1
