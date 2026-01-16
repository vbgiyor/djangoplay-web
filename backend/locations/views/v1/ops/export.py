import csv

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from locations.models import CustomCity


@extend_schema(
    tags=["Locations: Export"],
    summary="Export cities as CSV",
    exclude=True,
)
class CityExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="cities.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Name", "Region", "Country"])

        for city in CustomCity.objects.select_related("subregion__region__country"):
            writer.writerow([
                city.id,
                city.name,
                city.subregion.region.name if city.subregion else "",
                city.subregion.region.country.name if city.subregion else "",
            ])

        return response
