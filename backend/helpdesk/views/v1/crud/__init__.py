from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .bug import BugReportViewSet
from .file_upload import FileUploadViewSet
from .support import SupportViewSet

app_name = "helpdesk_v1_crud"

router = DefaultRouter()
router.register(r"supports", SupportViewSet)
router.register(r"bugs", BugReportViewSet)
router.register(r"file-uploads", FileUploadViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
