from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import EmployeeType
from users.serializers.v1.read import EmployeeTypeReadSerializerV1


@extend_schema(tags=["Users: Employee Type"])
class EmployeeTypeListAPIView(BaseListAPIView):
    queryset = EmployeeType.objects.filter(deleted_at__isnull=True)
    serializer_class = EmployeeTypeReadSerializerV1
