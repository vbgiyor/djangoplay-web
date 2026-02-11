from django.urls import path

from .address import AddressDetailAPIView
from .department import DepartmentDetailAPIView
from .employee_type import EmployeeTypeDetailAPIView
from .employment_status import EmploymentStatusDetailAPIView
from .leave_application import LeaveApplicationDetailAPIView
from .leave_balance import LeaveBalanceDetailAPIView
from .leave_type import LeaveTypeDetailAPIView
from .member_profile import MemberProfileDetailAPIView
from .member_status import MemberStatusDetailAPIView
from .role import RoleDetailAPIView
from .team import TeamDetailAPIView

urlpatterns = [
    path("addresses/<int:pk>/", AddressDetailAPIView.as_view()),
    path("departments/<int:pk>/", DepartmentDetailAPIView.as_view()),
    path("employee-types/<int:pk>/", EmployeeTypeDetailAPIView.as_view()),
    path("employment-statuses/<int:pk>/", EmploymentStatusDetailAPIView.as_view()),
    path("leave-applications/<int:pk>/", LeaveApplicationDetailAPIView.as_view()),
    path("leave-balances/<int:pk>/", LeaveBalanceDetailAPIView.as_view()),
    path("leave-types/<int:pk>/", LeaveTypeDetailAPIView.as_view()),
    path("members/<int:pk>/", MemberProfileDetailAPIView.as_view()),
    path("member-statuses/<int:pk>/", MemberStatusDetailAPIView.as_view()),
    path("roles/<int:pk>/", RoleDetailAPIView.as_view()),
    path("teams/<int:pk>/", TeamDetailAPIView.as_view()),
]
