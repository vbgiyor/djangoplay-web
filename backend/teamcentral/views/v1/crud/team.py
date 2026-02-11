from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from teamcentral.models import Team
from teamcentral.serializers.v1.read import TeamReadSerializerV1
from teamcentral.serializers.v1.write import TeamWriteSerializerV1


@extend_schema(tags=["Teamcentral: Team"])
class TeamViewSet(BaseViewSet):
    queryset = Team.objects.filter(deleted_at__isnull=True)

    read_serializer_class = TeamReadSerializerV1
    write_serializer_class = TeamWriteSerializerV1
