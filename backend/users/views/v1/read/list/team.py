from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import Team
from users.serializers.v1.read import TeamReadSerializerV1


@extend_schema(tags=["Users: Team"])
class TeamListAPIView(BaseListAPIView):
    queryset = Team.objects.filter(deleted_at__isnull=True)
    serializer_class = TeamReadSerializerV1
