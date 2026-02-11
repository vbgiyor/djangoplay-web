from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import Department
from teamcentral.serializers.v1.read import DepartmentReadSerializerV1


@extend_schema(tags=["Teamcentral: Department"])
class DepartmentDetailAPIView(RetrieveAPIView):
    queryset = Department.objects.filter(deleted_at__isnull=True)
    serializer_class = DepartmentReadSerializerV1
