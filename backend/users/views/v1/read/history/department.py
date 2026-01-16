from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import Department
from users.serializers.v1.read import DepartmentReadSerializerV1


@extend_schema(tags=["Users: Department"])
class DepartmentHistoryAPIView(BaseHistoryListAPIView):
    queryset = Department.objects.all()
    history_queryset = Department.history.all()
    serializer_class = DepartmentReadSerializerV1
