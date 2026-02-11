from django.urls import path

from .address import AddressListAPIView
from .department import DepartmentListAPIView
from .employee_type import EmployeeTypeListAPIView
from .employment_status import EmploymentStatusListAPIView
from .leave_application import LeaveApplicationListAPIView
from .leave_balance import LeaveBalanceListAPIView
from .leave_type import LeaveTypeListAPIView
from .member_profile import MemberProfileListAPIView
from .member_status import MemberStatusListAPIView
from .role import RoleListAPIView
from .team import TeamListAPIView

urlpatterns = [
    path("addresses/", AddressListAPIView.as_view()),
    path("departments/", DepartmentListAPIView.as_view()),
    path("employee-types/", EmployeeTypeListAPIView.as_view()),
    path("employment-statuses/", EmploymentStatusListAPIView.as_view()),
    path("leave-applications/", LeaveApplicationListAPIView.as_view()),
    path("leave-balances/", LeaveBalanceListAPIView.as_view()),
    path("leave-types/", LeaveTypeListAPIView.as_view()),
    path("members/", MemberProfileListAPIView.as_view()),
    path("member-statuses/", MemberStatusListAPIView.as_view()),
    path("roles/", RoleListAPIView.as_view()),
    path("teams/", TeamListAPIView.as_view()),
]
