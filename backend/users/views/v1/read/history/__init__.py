from django.urls import path

from .address import AddressHistoryAPIView
from .department import DepartmentHistoryAPIView
from .employee import EmployeeHistoryAPIView
from .employee_type import EmployeeTypeHistoryAPIView
from .employment_status import EmploymentStatusHistoryAPIView
from .file_upload import FileUploadHistoryAPIView
from .leave_application import LeaveApplicationHistoryAPIView
from .leave_balance import LeaveBalanceHistoryAPIView
from .leave_type import LeaveTypeHistoryAPIView
from .member import MemberHistoryAPIView
from .member_status import MemberStatusHistoryAPIView
from .password_reset_request import PasswordResetRequestHistoryAPIView
from .role import RoleHistoryAPIView
from .signup_request import SignUpRequestHistoryAPIView
from .support import SupportHistoryAPIView
from .team import TeamHistoryAPIView
from .user_activity_log import UserActivityLogHistoryAPIView

urlpatterns = [
    path("addresses/", AddressHistoryAPIView.as_view()),
    path("departments/", DepartmentHistoryAPIView.as_view()),
    path("employees/", EmployeeHistoryAPIView.as_view()),
    path("employee-types/", EmployeeTypeHistoryAPIView.as_view()),
    path("employment-statuses/", EmploymentStatusHistoryAPIView.as_view()),
    path("leave-applications/", LeaveApplicationHistoryAPIView.as_view()),
    path("leave-balances/", LeaveBalanceHistoryAPIView.as_view()),
    path("leave-types/", LeaveTypeHistoryAPIView.as_view()),
    path("members/", MemberHistoryAPIView.as_view()),
    path("member-statuses/", MemberStatusHistoryAPIView.as_view()),
    path("roles/", RoleHistoryAPIView.as_view()),
    path("signup-requests/", SignUpRequestHistoryAPIView.as_view()),
    path("supports/", SupportHistoryAPIView.as_view()),
    path("teams/", TeamHistoryAPIView.as_view()),
    path("activity-logs/", UserActivityLogHistoryAPIView.as_view()),
    path("file-uploads/", FileUploadHistoryAPIView.as_view()),
    path("password-reset-requests/", PasswordResetRequestHistoryAPIView.as_view()),
]
