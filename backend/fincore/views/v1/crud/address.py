from drf_spectacular.utils import extend_schema
from fincore.models import Address
from fincore.permissions import FincorePermission
from fincore.serializers.v1.read.address import FincoreAddressReadSerializerV1
from fincore.serializers.v1.write.address import FincoreAddressWriteSerializerV1
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet


@extend_schema(tags=["Finance: Address"])
class AddressCrudViewSet(ModelViewSet):

    """
    Create / Update / Delete Address
    """

    queryset = Address.objects.all()
    permission_classes = [IsAuthenticated, FincorePermission]

    read_serializer_class = FincoreAddressReadSerializerV1
    write_serializer_class = FincoreAddressWriteSerializerV1

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return self.read_serializer_class
        return self.write_serializer_class
