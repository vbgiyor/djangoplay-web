from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from teamcentral.models import EmploymentStatus
from teamcentral.serializers.v1.read import EmploymentStatusReadSerializerV1


@extend_schema(tags=["Teamcentral: Employment Status"])
class EmploymentStatusHistoryAPIView(BaseHistoryListAPIView):
    queryset = EmploymentStatus.objects.all()
    history_queryset = EmploymentStatus.history.all()
    serializer_class = EmploymentStatusReadSerializerV1
