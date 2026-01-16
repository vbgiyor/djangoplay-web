from django.urls import path

from .address import AddressDetailAPIView
from .department import DepartmentDetailAPIView
from .employee import EmployeeDetailAPIView
from .employee_type import EmployeeTypeDetailAPIView
from .employment_status import EmploymentStatusDetailAPIView
from .file_upload import FileUploadDetailAPIView
from .leave_application import LeaveApplicationDetailAPIView
from .leave_balance import LeaveBalanceDetailAPIView
from .leave_type import LeaveTypeDetailAPIView
from .member import MemberDetailAPIView
from .member_status import MemberStatusDetailAPIView
from .password_reset_request import PasswordResetRequestDetailAPIView
from .role import RoleDetailAPIView
from .signup_request import SignUpRequestDetailAPIView
from .support import SupportDetailAPIView
from .team import TeamDetailAPIView
from .user_activity_log import UserActivityLogDetailAPIView

urlpatterns = [
    path("addresses/<int:pk>/", AddressDetailAPIView.as_view()),
    path("departments/<int:pk>/", DepartmentDetailAPIView.as_view()),
    path("employees/<int:pk>/", EmployeeDetailAPIView.as_view()),
    path("employee-types/<int:pk>/", EmployeeTypeDetailAPIView.as_view()),
    path("employment-statuses/<int:pk>/", EmploymentStatusDetailAPIView.as_view()),
    path("leave-applications/<int:pk>/", LeaveApplicationDetailAPIView.as_view()),
    path("leave-balances/<int:pk>/", LeaveBalanceDetailAPIView.as_view()),
    path("leave-types/<int:pk>/", LeaveTypeDetailAPIView.as_view()),
    path("members/<int:pk>/", MemberDetailAPIView.as_view()),
    path("member-statuses/<int:pk>/", MemberStatusDetailAPIView.as_view()),
    path("roles/<int:pk>/", RoleDetailAPIView.as_view()),
    path("signup-requests/<int:pk>/", SignUpRequestDetailAPIView.as_view()),
    path("supports/<int:pk>/", SupportDetailAPIView.as_view()),
    path("teams/<int:pk>/", TeamDetailAPIView.as_view()),
    path("activity-logs/<int:pk>/", UserActivityLogDetailAPIView.as_view()),
    path("file-uploads/<int:pk>/", FileUploadDetailAPIView.as_view()),
    path("password-reset-requests/<int:pk>/", PasswordResetRequestDetailAPIView.as_view()),
]
