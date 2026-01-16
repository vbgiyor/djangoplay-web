import csv

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from users.models import Employee


@extend_schema(
    tags=["Users: Export"],
    summary="Export employees as CSV",
    exclude=True,
)
class EmployeeExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="employees.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Email", "Name", "Department", "Role"])

        for emp in Employee.objects.select_related("department", "role"):
            writer.writerow([
                emp.id,
                emp.email,
                emp.get_full_name(),
                emp.department.name if emp.department else "",
                emp.role.name if emp.role else "",
            ])

        return response
