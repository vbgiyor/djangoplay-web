from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from locations.exceptions import InvalidLocationData
from locations.models import Timezone
from locations.serializers import TimezoneReadSerializerV1


@extend_schema(tags=["Locations: Region"])
class TimezoneDetailAPIView(RetrieveAPIView):
    queryset = Timezone.objects.filter(deleted_at__isnull=True)
    serializer_class = TimezoneReadSerializerV1
    error_class = InvalidLocationData
