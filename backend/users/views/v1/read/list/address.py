from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView
from utilities.api.pagination import StandardResultsSetPagination

from users.models import Address
from users.serializers.v1.read import AddressReadSerializerV1


@extend_schema(tags=["Users: Address"])
class AddressListAPIView(BaseListAPIView):
    queryset = Address.objects.filter(deleted_at__isnull=True)
    serializer_class = AddressReadSerializerV1
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["city", "state"]
    search_fields = ["address", "city"]
