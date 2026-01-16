from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import Department
from users.serializers.v1.read import DepartmentReadSerializerV1


@extend_schema(tags=["Users: Department"])
class DepartmentDetailAPIView(RetrieveAPIView):
    queryset = Department.objects.filter(deleted_at__isnull=True)
    serializer_class = DepartmentReadSerializerV1
