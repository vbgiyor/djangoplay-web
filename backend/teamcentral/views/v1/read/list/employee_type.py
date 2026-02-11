from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from teamcentral.models import EmployeeType
from teamcentral.serializers.v1.read import EmployeeTypeReadSerializerV1


@extend_schema(tags=["Teamcentral: Employee Type"])
class EmployeeTypeListAPIView(BaseListAPIView):
    queryset = EmployeeType.objects.filter(deleted_at__isnull=True)
    serializer_class = EmployeeTypeReadSerializerV1
