from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import EmploymentStatus
from teamcentral.serializers.v1.read import EmploymentStatusReadSerializerV1


@extend_schema(tags=["Teamcentral: Employment Status"])
class EmploymentStatusDetailAPIView(RetrieveAPIView):
    queryset = EmploymentStatus.objects.filter(deleted_at__isnull=True)
    serializer_class = EmploymentStatusReadSerializerV1
