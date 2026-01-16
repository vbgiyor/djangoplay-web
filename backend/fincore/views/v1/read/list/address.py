from drf_spectacular.utils import extend_schema
from fincore.models import Address
from fincore.permissions import FincorePermission
from fincore.serializers.v1.read.address import FincoreAddressReadSerializerV1
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated


@extend_schema(tags=["Finance: Address"])
class AddressListAPIView(ListAPIView):
    queryset = Address.objects.all()
    serializer_class = FincoreAddressReadSerializerV1
    permission_classes = [IsAuthenticated, FincorePermission]
