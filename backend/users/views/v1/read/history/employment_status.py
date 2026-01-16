from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import EmploymentStatus
from users.serializers.v1.read import EmploymentStatusReadSerializerV1


@extend_schema(tags=["Users: Employment Status"])
class EmploymentStatusHistoryAPIView(BaseHistoryListAPIView):
    queryset = EmploymentStatus.objects.all()
    history_queryset = EmploymentStatus.history.all()
    serializer_class = EmploymentStatusReadSerializerV1
