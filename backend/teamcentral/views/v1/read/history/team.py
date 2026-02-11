from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from teamcentral.models import Team
from teamcentral.serializers.v1.read import TeamReadSerializerV1


@extend_schema(tags=["Teamcentral: Team"])
class TeamHistoryAPIView(BaseHistoryListAPIView):
    queryset = Team.objects.all()
    history_queryset = Team.history.all()
    serializer_class = TeamReadSerializerV1
