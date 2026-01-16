from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

from invoices.models.status import Status
from invoices.serializers.v1.read import StatusReadSerializer
from invoices.serializers.v1.write import StatusWriteSerializer


@extend_schema(tags=["Invoices: Status"])
class StatusViewSet(ModelViewSet):
    queryset = Status.objects.filter(is_active=True).order_by("name")

    read_serializer_class = StatusReadSerializer
    write_serializer_class = StatusWriteSerializer

    def get_serializer_class(self):
        return (
            self.write_serializer_class
            if self.action in ("create", "update", "partial_update")
            else self.read_serializer_class
        )
