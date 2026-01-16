from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import Employee
from users.serializers.v1.read import EmployeeReadSerializerV1
from users.serializers.v1.write import EmployeeWriteSerializerV1


@extend_schema(tags=["Users: Employee"])
class EmployeeViewSet(BaseViewSet):
    queryset = Employee.objects.filter(deleted_at__isnull=True)

    read_serializer_class = EmployeeReadSerializerV1
    write_serializer_class = EmployeeWriteSerializerV1

    filterset_fields = ["department", "role", "team", "employment_status"]
    search_fields = ["username", "email", "employee_code"]
