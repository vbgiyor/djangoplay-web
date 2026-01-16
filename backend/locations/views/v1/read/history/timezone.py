from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from locations.models import Timezone
from locations.serializers import TimezoneReadSerializerV1


@extend_schema(tags=["Locations: Timezone"])
class TimezoneHistoryAPIView(BaseHistoryListAPIView):
    queryset = Timezone.objects.all()
    history_queryset = Timezone.history.all()
    serializer_class = TimezoneReadSerializerV1
