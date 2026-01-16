from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from industries.exceptions import InvalidIndustryData
from industries.models import Industry
from industries.serializers.v1.read import IndustryReadSerializerV1


@extend_schema(tags=["Industries"])
class IndustryDetailAPIView(RetrieveAPIView):
    queryset = Industry.objects.filter(deleted_at__isnull=True)
    serializer_class = IndustryReadSerializerV1
    error_class = InvalidIndustryData
