from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import Team
from teamcentral.serializers.v1.read import TeamReadSerializerV1


@extend_schema(tags=["Teamcentral: Team"])
class TeamDetailAPIView(RetrieveAPIView):
    queryset = Team.objects.filter(deleted_at__isnull=True)
    serializer_class = TeamReadSerializerV1
