from django.urls import path

from .address import AddressHistoryAPIView
from .department import DepartmentHistoryAPIView
from .employee_type import EmployeeTypeHistoryAPIView
from .employment_status import EmploymentStatusHistoryAPIView
from .leave_application import LeaveApplicationHistoryAPIView
from .leave_balance import LeaveBalanceHistoryAPIView
from .leave_type import LeaveTypeHistoryAPIView
from .member_profile import MemberProfileHistoryAPIView
from .member_status import MemberStatusHistoryAPIView
from .role import RoleHistoryAPIView
from .team import TeamHistoryAPIView

urlpatterns = [
    path("addresses/", AddressHistoryAPIView.as_view()),
    path("departments/", DepartmentHistoryAPIView.as_view()),
    path("employee-types/", EmployeeTypeHistoryAPIView.as_view()),
    path("employment-statuses/", EmploymentStatusHistoryAPIView.as_view()),
    path("leave-applications/", LeaveApplicationHistoryAPIView.as_view()),
    path("leave-balances/", LeaveBalanceHistoryAPIView.as_view()),
    path("leave-types/", LeaveTypeHistoryAPIView.as_view()),
    path("member-profiles/", MemberProfileHistoryAPIView.as_view()),
    path("member-statuses/", MemberStatusHistoryAPIView.as_view()),
    path("roles/", RoleHistoryAPIView.as_view()),
    path("teams/", TeamHistoryAPIView.as_view()),
]
