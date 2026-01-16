from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import EmployeeType
from users.serializers.v1.read import EmployeeTypeReadSerializerV1
from users.serializers.v1.write import EmployeeTypeWriteSerializerV1


@extend_schema(tags=["Users: Employee Type"])
class EmployeeTypeViewSet(BaseViewSet):
    queryset = EmployeeType.objects.filter(deleted_at__isnull=True)

    read_serializer_class = EmployeeTypeReadSerializerV1
    write_serializer_class = EmployeeTypeWriteSerializerV1
