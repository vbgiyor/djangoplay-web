from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from teamcentral.models import MemberProfile
from teamcentral.serializers.v1.read import MemberProfileReadSerializerV1
from teamcentral.serializers.v1.write import MemberProfileWriteSerializerV1


@extend_schema(tags=["Teamcentral: Member"])
class MemberProfileViewSet(BaseViewSet):
    queryset = MemberProfile.objects.filter(deleted_at__isnull=True)

    read_serializer_class = MemberProfileReadSerializerV1
    write_serializer_class = MemberProfileWriteSerializerV1
