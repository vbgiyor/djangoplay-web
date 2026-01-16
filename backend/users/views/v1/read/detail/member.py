from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import Member
from users.serializers.v1.read import MemberReadSerializerV1


@extend_schema(tags=["Users: Member"])
class MemberDetailAPIView(RetrieveAPIView):
    queryset = Member.objects.filter(deleted_at__isnull=True)
    serializer_class = MemberReadSerializerV1
