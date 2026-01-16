from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import EmploymentStatus
from users.serializers.v1.read import EmploymentStatusReadSerializerV1


@extend_schema(tags=["Users: Employment Status"])
class EmploymentStatusListAPIView(BaseListAPIView):
    queryset = EmploymentStatus.objects.filter(deleted_at__isnull=True)
    serializer_class = EmploymentStatusReadSerializerV1
