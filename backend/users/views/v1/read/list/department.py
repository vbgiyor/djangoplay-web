from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import Department
from users.serializers.v1.read import DepartmentReadSerializerV1


@extend_schema(tags=["Users: Department"])
class DepartmentListAPIView(BaseListAPIView):
    queryset = Department.objects.filter(deleted_at__isnull=True)
    serializer_class = DepartmentReadSerializerV1
