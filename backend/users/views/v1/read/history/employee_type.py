from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import EmployeeType
from users.serializers.v1.read import EmployeeTypeReadSerializerV1


@extend_schema(tags=["Users: Employee Type"])
class EmployeeTypeHistoryAPIView(BaseHistoryListAPIView):
    queryset = EmployeeType.objects.all()
    history_queryset = EmployeeType.history.all()
    serializer_class = EmployeeTypeReadSerializerV1
