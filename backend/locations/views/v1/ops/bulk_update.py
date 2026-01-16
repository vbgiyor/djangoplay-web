from drf_spectacular.utils import extend_schema
from utilities.api.bulk_views import BaseBulkUpdateAPIView

from locations.models import (
    CustomCity,
    CustomCountry,
    CustomRegion,
    CustomSubRegion,
    GlobalRegion,
    Timezone,
)
from locations.serializers import (
    CityWriteSerializerV1,
    CountryWriteSerializerV1,
    GlobalRegionWriteSerializerV1,
    RegionWriteSerializerV1,
    SubRegionWriteSerializerV1,
    TimezoneWriteSerializerV1,
)


@extend_schema(tags=["Locations: Bulk"])
class GlobalRegionBulkUpdateAPIView(BaseBulkUpdateAPIView):
    model = GlobalRegion
    serializer_class = GlobalRegionWriteSerializerV1
    allowed_fields = {"name"}
    change_reason = "Bulk update of global regions"


@extend_schema(tags=["Locations: Bulk"])
class CustomCountryBulkUpdateAPIView(BaseBulkUpdateAPIView):
    model = CustomCountry
    serializer_class = CountryWriteSerializerV1
    allowed_fields = {"name", "iso2", "phone_code"}
    change_reason = "Bulk update of countries"


@extend_schema(tags=["Locations: Bulk"])
class CustomRegionBulkUpdateAPIView(BaseBulkUpdateAPIView):
    model = CustomRegion
    serializer_class = RegionWriteSerializerV1
    allowed_fields = {"name", "country"}
    change_reason = "Bulk update of regions"


@extend_schema(tags=["Locations: Bulk"])
class CustomSubRegionBulkUpdateAPIView(BaseBulkUpdateAPIView):
    model = CustomSubRegion
    serializer_class = SubRegionWriteSerializerV1
    allowed_fields = {"name", "region"}
    change_reason = "Bulk update of subregions"


@extend_schema(tags=["Locations: Bulk"])
class CityBulkUpdateAPIView(BaseBulkUpdateAPIView):
    model = CustomCity
    serializer_class = CityWriteSerializerV1
    allowed_fields = {"name", "region", "subregion"}
    change_reason = "Bulk update of cities"


@extend_schema(tags=["Locations: Bulk"])
class TimezoneBulkUpdateAPIView(BaseBulkUpdateAPIView):
    model = Timezone
    serializer_class = TimezoneWriteSerializerV1
    allowed_fields = {"display_name"}
    change_reason = "Bulk update of timezones"
