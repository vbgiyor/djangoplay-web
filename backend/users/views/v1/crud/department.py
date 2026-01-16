from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import Department
from users.serializers.v1.read import DepartmentReadSerializerV1
from users.serializers.v1.write import DepartmentWriteSerializerV1


@extend_schema(tags=["Users: Department"])
class DepartmentViewSet(BaseViewSet):
    queryset = Department.objects.filter(deleted_at__isnull=True)

    read_serializer_class = DepartmentReadSerializerV1
    write_serializer_class = DepartmentWriteSerializerV1
