from drf_spectacular.utils import extend_schema
from fincore.models import TaxProfile
from fincore.permissions import FincorePermission
from fincore.serializers.v1.read.tax_profile import TaxProfileReadSerializerV1
from fincore.serializers.v1.write.tax_profile import TaxProfileWriteSerializerV1
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet


@extend_schema(tags=["Finance: Tax Profile"])
class TaxProfileCRUDViewSet(ModelViewSet):

    """
    CRUD ViewSet for TaxProfile.
    """

    permission_classes = (IsAuthenticated, FincorePermission)
    queryset = TaxProfile.objects.all()

    read_serializer_class = TaxProfileReadSerializerV1
    write_serializer_class = TaxProfileWriteSerializerV1

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return self.write_serializer_class
        return self.read_serializer_class
