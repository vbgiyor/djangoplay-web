from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from teamcentral.models import Department
from teamcentral.serializers.v1.read import DepartmentReadSerializerV1


@extend_schema(tags=["Teamcentral: Department"])
class DepartmentHistoryAPIView(BaseHistoryListAPIView):
    queryset = Department.objects.all()
    history_queryset = Department.history.all()
    serializer_class = DepartmentReadSerializerV1
