from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import Member
from users.serializers.v1.read import MemberReadSerializerV1
from users.serializers.v1.write import MemberWriteSerializerV1


@extend_schema(tags=["Users: Member"])
class MemberViewSet(BaseViewSet):
    queryset = Member.objects.filter(deleted_at__isnull=True)

    read_serializer_class = MemberReadSerializerV1
    write_serializer_class = MemberWriteSerializerV1
