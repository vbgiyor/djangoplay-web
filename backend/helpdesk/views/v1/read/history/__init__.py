from django.urls import path

from .bug import BugReportHistoryAPIView
from .file_upload import FileUploadHistoryAPIView
from .support import SupportHistoryAPIView

urlpatterns = [
    path("file-uploads/", FileUploadHistoryAPIView.as_view()),
    path("support/", SupportHistoryAPIView.as_view()),
    path("bugs/", BugReportHistoryAPIView.as_view()),
]
