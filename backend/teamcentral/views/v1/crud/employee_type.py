from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from teamcentral.models import EmployeeType
from teamcentral.serializers.v1.read import EmployeeTypeReadSerializerV1
from teamcentral.serializers.v1.write import EmployeeTypeWriteSerializerV1


@extend_schema(tags=["Teamcentral: Employee Type"])
class EmployeeTypeViewSet(BaseViewSet):
    queryset = EmployeeType.objects.filter(deleted_at__isnull=True)

    read_serializer_class = EmployeeTypeReadSerializerV1
    write_serializer_class = EmployeeTypeWriteSerializerV1
