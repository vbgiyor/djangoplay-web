from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from teamcentral.models import Department
from teamcentral.serializers.v1.read import DepartmentReadSerializerV1


@extend_schema(tags=["Teamcentral: Department"])
class DepartmentListAPIView(BaseListAPIView):
    queryset = Department.objects.filter(deleted_at__isnull=True)
    serializer_class = DepartmentReadSerializerV1
