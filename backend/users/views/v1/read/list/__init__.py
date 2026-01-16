from django.urls import path

from .address import AddressListAPIView
from .department import DepartmentListAPIView
from .employee import EmployeeListAPIView
from .employee_type import EmployeeTypeListAPIView
from .employment_status import EmploymentStatusListAPIView
from .file_upload import FileUploadListAPIView
from .leave_application import LeaveApplicationListAPIView
from .leave_balance import LeaveBalanceListAPIView
from .leave_type import LeaveTypeListAPIView
from .member import MemberListAPIView
from .member_status import MemberStatusListAPIView
from .password_reset_request import PasswordResetRequestListAPIView
from .role import RoleListAPIView
from .signup_request import SignUpRequestListAPIView
from .support import SupportListAPIView
from .team import TeamListAPIView
from .user_activity_log import UserActivityLogListAPIView

urlpatterns = [
    path("addresses/", AddressListAPIView.as_view()),
    path("departments/", DepartmentListAPIView.as_view()),
    path("employees/", EmployeeListAPIView.as_view()),
    path("employee-types/", EmployeeTypeListAPIView.as_view()),
    path("employment-statuses/", EmploymentStatusListAPIView.as_view()),
    path("leave-applications/", LeaveApplicationListAPIView.as_view()),
    path("leave-balances/", LeaveBalanceListAPIView.as_view()),
    path("leave-types/", LeaveTypeListAPIView.as_view()),
    path("members/", MemberListAPIView.as_view()),
    path("member-statuses/", MemberStatusListAPIView.as_view()),
    path("roles/", RoleListAPIView.as_view()),
    path("signup-requests/", SignUpRequestListAPIView.as_view()),
    path("supports/", SupportListAPIView.as_view()),
    path("teams/", TeamListAPIView.as_view()),
    path("activity-logs/", UserActivityLogListAPIView.as_view()),
    path("file-uploads/", FileUploadListAPIView.as_view()),
    path("password-reset-requests/", PasswordResetRequestListAPIView.as_view()),
]
