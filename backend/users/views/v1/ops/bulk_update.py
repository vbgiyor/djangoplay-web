from drf_spectacular.utils import extend_schema
from utilities.api.bulk_views import BaseBulkUpdateAPIView

from users.models import (
    Department,
    Role,
    Team,
)
from users.serializers.v1.write import (
    DepartmentWriteSerializerV1,
    RoleWriteSerializerV1,
    TeamWriteSerializerV1,
)


@extend_schema(tags=["Users: Bulk"])
class DepartmentBulkUpdateAPIView(BaseBulkUpdateAPIView):
    model = Department
    serializer_class = DepartmentWriteSerializerV1
    allowed_fields = {"name"}
    change_reason = "Bulk update of departments"


@extend_schema(tags=["Users: Bulk"])
class RoleBulkUpdateAPIView(BaseBulkUpdateAPIView):
    model = Role
    serializer_class = RoleWriteSerializerV1
    allowed_fields = {"name"}
    change_reason = "Bulk update of roles"


@extend_schema(tags=["Users: Bulk"])
class TeamBulkUpdateAPIView(BaseBulkUpdateAPIView):
    model = Team
    serializer_class = TeamWriteSerializerV1
    allowed_fields = {"name"}
    change_reason = "Bulk update of teams"
