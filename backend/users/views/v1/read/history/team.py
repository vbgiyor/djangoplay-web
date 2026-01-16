from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import Team
from users.serializers.v1.read import TeamReadSerializerV1


@extend_schema(tags=["Users: Team"])
class TeamHistoryAPIView(BaseHistoryListAPIView):
    queryset = Team.objects.all()
    history_queryset = Team.history.all()
    serializer_class = TeamReadSerializerV1
