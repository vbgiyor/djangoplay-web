from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from industries.models import Industry
from industries.serializers.v1.read import IndustryReadSerializerV1


@extend_schema(tags=["Industries"])
class IndustryHistoryAPIView(BaseHistoryListAPIView):
    queryset = Industry.objects.all()
    history_queryset = Industry.history.all()
    serializer_class = IndustryReadSerializerV1
