from django.urls import include, path

app_name = "invoices_v1_read"

urlpatterns = [
    path("list/", include("invoices.views.v1.read.list")),
    path("detail/", include("invoices.views.v1.read.detail")),
    path("history/", include("invoices.views.v1.read.history")),
]
