from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .address import AddressViewSet
from .department import DepartmentViewSet
from .employee import EmployeeViewSet
from .employee_type import EmployeeTypeViewSet
from .employment_status import EmploymentStatusViewSet
from .file_upload import FileUploadViewSet
from .leave_application import LeaveApplicationViewSet
from .leave_balance import LeaveBalanceViewSet
from .leave_type import LeaveTypeViewSet
from .member import MemberViewSet
from .member_status import MemberStatusViewSet
from .role import RoleViewSet
from .signup_request import SignUpRequestViewSet
from .support import SupportViewSet
from .team import TeamViewSet

app_name = "users_v1_crud"

router = DefaultRouter()
router.register(r"addresses", AddressViewSet)
router.register(r"departments", DepartmentViewSet)
router.register(r"employees", EmployeeViewSet)
router.register(r"employee-types", EmployeeTypeViewSet)
router.register(r"employment-statuses", EmploymentStatusViewSet)
router.register(r"file-uploads", FileUploadViewSet)
router.register(r"leave-applications", LeaveApplicationViewSet)
router.register(r"leave-balances", LeaveBalanceViewSet)
router.register(r"leave-types", LeaveTypeViewSet)
router.register(r"members", MemberViewSet)
router.register(r"member-statuses", MemberStatusViewSet)
router.register(r"roles", RoleViewSet)
router.register(r"signup-requests", SignUpRequestViewSet)
router.register(r"supports", SupportViewSet)
router.register(r"teams", TeamViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
