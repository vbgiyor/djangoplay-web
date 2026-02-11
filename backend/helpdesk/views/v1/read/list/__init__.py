from django.urls import path

from .bug import BugReportListAPIView
from .file_upload import FileUploadListAPIView
from .support import SupportListAPIView

urlpatterns = [
    path("supports/", SupportListAPIView.as_view()),
    path("file-uploads/", FileUploadListAPIView.as_view()),
    path("bugs/", BugReportListAPIView.as_view()),
]
