from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from teamcentral.models import EmploymentStatus
from teamcentral.serializers.v1.read import EmploymentStatusReadSerializerV1
from teamcentral.serializers.v1.write import EmploymentStatusWriteSerializerV1


@extend_schema(tags=["Teamcentral: Employment Status"])
class EmploymentStatusViewSet(BaseViewSet):
    queryset = EmploymentStatus.objects.filter(deleted_at__isnull=True)

    read_serializer_class = EmploymentStatusReadSerializerV1
    write_serializer_class = EmploymentStatusWriteSerializerV1
