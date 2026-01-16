from drf_spectacular.utils import extend_schema
from entities.models import Entity
from entities.serializers.v1.read import EntityReadSerializerV1
from utilities.api.generic_views import BaseHistoryListAPIView


@extend_schema(tags=["Business"])
class EntityHistoryAPIView(BaseHistoryListAPIView):
    queryset = Entity.objects.all()
    history_queryset = Entity.history.all()
    serializer_class = EntityReadSerializerV1
