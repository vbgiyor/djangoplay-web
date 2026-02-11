from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from teamcentral.models import Address
from teamcentral.serializers.v1.read import AddressReadSerializerV1
from teamcentral.serializers.v1.write import AddressWriteSerializerV1


@extend_schema(tags=["Teamcentral: Address"])
class AddressViewSet(BaseViewSet):
    queryset = Address.objects.filter(deleted_at__isnull=True)

    read_serializer_class = AddressReadSerializerV1
    write_serializer_class = AddressWriteSerializerV1

    filterset_fields = ["city", "state"]
    search_fields = ["address"]
