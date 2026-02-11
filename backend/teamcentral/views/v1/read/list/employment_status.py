from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from teamcentral.models import EmploymentStatus
from teamcentral.serializers.v1.read import EmploymentStatusReadSerializerV1


@extend_schema(tags=["Teamcentral: Employment Status"])
class EmploymentStatusListAPIView(BaseListAPIView):
    queryset = EmploymentStatus.objects.filter(deleted_at__isnull=True)
    serializer_class = EmploymentStatusReadSerializerV1
