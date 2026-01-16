from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import Employee
from users.serializers.v1.read import EmployeeReadSerializerV1


@extend_schema(tags=["Users: Employee"])
class EmployeeDetailAPIView(RetrieveAPIView):
    queryset = Employee.objects.filter(deleted_at__isnull=True)
    serializer_class = EmployeeReadSerializerV1
