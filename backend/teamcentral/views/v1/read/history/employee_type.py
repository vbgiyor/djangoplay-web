from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from teamcentral.models import EmployeeType
from teamcentral.serializers.v1.read import EmployeeTypeReadSerializerV1


@extend_schema(tags=["Teamcentral: Employee Type"])
class EmployeeTypeHistoryAPIView(BaseHistoryListAPIView):
    queryset = EmployeeType.objects.all()
    history_queryset = EmployeeType.history.all()
    serializer_class = EmployeeTypeReadSerializerV1
