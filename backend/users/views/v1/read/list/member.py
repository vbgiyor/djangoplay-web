from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import Member
from users.serializers.v1.read import MemberReadSerializerV1


@extend_schema(tags=["Users: Member"])
class MemberListAPIView(BaseListAPIView):
    queryset = Member.objects.filter(deleted_at__isnull=True)
    serializer_class = MemberReadSerializerV1
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    search_fields = ["email", "member_code"]
