from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from teamcentral.models import Department
from teamcentral.serializers.v1.read import DepartmentReadSerializerV1
from teamcentral.serializers.v1.write import DepartmentWriteSerializerV1


@extend_schema(tags=["Teamcentral: Department"])
class DepartmentViewSet(BaseViewSet):
    queryset = Department.objects.filter(deleted_at__isnull=True)

    read_serializer_class = DepartmentReadSerializerV1
    write_serializer_class = DepartmentWriteSerializerV1
