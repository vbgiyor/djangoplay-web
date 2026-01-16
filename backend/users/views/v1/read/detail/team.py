from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import Team
from users.serializers.v1.read import TeamReadSerializerV1


@extend_schema(tags=["Users: Team"])
class TeamDetailAPIView(RetrieveAPIView):
    queryset = Team.objects.filter(deleted_at__isnull=True)
    serializer_class = TeamReadSerializerV1
