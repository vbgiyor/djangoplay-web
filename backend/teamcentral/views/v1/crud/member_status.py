from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from teamcentral.models import MemberStatus
from teamcentral.serializers.v1.read import MemberStatusReadSerializerV1
from teamcentral.serializers.v1.write import MemberStatusWriteSerializerV1


@extend_schema(tags=["Teamcentral: Member Status"])
class MemberStatusViewSet(BaseViewSet):
    queryset = MemberStatus.objects.filter(deleted_at__isnull=True)

    read_serializer_class = MemberStatusReadSerializerV1
    write_serializer_class = MemberStatusWriteSerializerV1
