from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import EmployeeType
from teamcentral.serializers.v1.read import EmployeeTypeReadSerializerV1


@extend_schema(tags=["Teamcentral: Employee Type"])
class EmployeeTypeDetailAPIView(RetrieveAPIView):
    queryset = EmployeeType.objects.filter(deleted_at__isnull=True)
    serializer_class = EmployeeTypeReadSerializerV1
