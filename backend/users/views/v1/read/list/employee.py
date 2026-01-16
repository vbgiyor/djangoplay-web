from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView
from utilities.api.pagination import StandardResultsSetPagination

from users.models import Employee
from users.serializers.v1.read import EmployeeReadSerializerV1


@extend_schema(tags=["Users: Employee"])
class EmployeeListAPIView(BaseListAPIView):
    queryset = Employee.objects.filter(deleted_at__isnull=True)
    serializer_class = EmployeeReadSerializerV1
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["department", "role", "team", "employment_status"]
    search_fields = ["username", "email", "employee_code"]
