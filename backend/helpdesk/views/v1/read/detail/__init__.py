from django.urls import path

from .bug import BugReportDetailAPIView
from .file_upload import FileUploadDetailAPIView
from .support import SupportDetailAPIView

urlpatterns = [
    path("bugs/<int:pk>/", BugReportDetailAPIView.as_view()),
    path("supports/<int:pk>/", SupportDetailAPIView.as_view()),
    path("file-uploads/<int:pk>/", FileUploadDetailAPIView.as_view()),
]
