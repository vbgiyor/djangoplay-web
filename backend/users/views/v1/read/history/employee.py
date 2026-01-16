from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import Employee
from users.serializers.v1.read import EmployeeReadSerializerV1


@extend_schema(tags=["Users: Employee"])
class EmployeeHistoryAPIView(BaseHistoryListAPIView):
    queryset = Employee.objects.all()
    history_queryset = Employee.history.all()
    serializer_class = EmployeeReadSerializerV1
