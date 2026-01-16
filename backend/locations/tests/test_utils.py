import uuid

from django.contrib.auth import get_user_model

from locations.models.custom_city import CustomCity
from locations.models.custom_country import CustomCountry
from locations.models.custom_region import CustomRegion
from locations.models.custom_subregion import CustomSubRegion
from locations.models.global_region import GlobalRegion
from locations.models.location import Location
from locations.models.timezone import Timezone


def create_test_user(email='testuser@example.com', password='testpass123'):
    """Create a test user."""
    User = get_user_model()
    try:
        user = User.objects.get(username="admin")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username="redstar",
            email=email,
            password=password
        )
    return user

def create_test_country(name=None, country_code='TC', currency_code='TCT', country_phone_code='+123', postal_code_regex=r'^TKCA\s1ZZ$'):
    """Create a test CustomCountry with unique name."""
    if name is None:
        name = f'Test Country {uuid.uuid4().hex[:8]}'
    return CustomCountry.objects.create(
        name=name,
        country_code=country_code,
        currency_code=currency_code,
        country_phone_code=country_phone_code,
        postal_code_regex=postal_code_regex,
        created_by=None,
        updated_by=None
    )

def create_test_region(name=None, country=None, code='TEST'):
    """Create a test CustomRegion linked to a country."""
    if country is None:
        country = create_test_country()
    if name is None:
        name = f'Test Region {uuid.uuid4().hex[:8]}'
    return CustomRegion.objects.create(
        name=name,
        country=country,
        code=code,
        created_by=None,
        updated_by=None
    )

def create_test_subregion(name=None, region=None, code='SUBTEST'):
    """Create a test CustomSubRegion linked to a region."""
    if region is None:
        country = create_test_country()
        region = create_test_region(country=country)
    if name is None:
        name = f'Test SubRegion {uuid.uuid4().hex[:8]}'
    return CustomSubRegion.objects.create(
        name=name,
        region=region,
        code=code,
        created_by=None,
        updated_by=None
    )

def create_test_city(name=None, country=None, region=None, subregion=None, pin_code=None, timezone=None):
    """Create a test CustomCity."""
    if country is None:
        country = create_test_country()
    if region is None and subregion:
        region = create_test_region(country=country)
    if subregion is None and region:
        subregion = create_test_subregion(region=region)
    if name is None:
        name = f'Test City {uuid.uuid4().hex[:8]}'
    if timezone is None:
        timezone = create_test_timezone(country_code=country.country_code)
    if pin_code is None:
        pin_code = 'TKCA 1ZZ' if country.country_code == 'TC' else '123456'
    return CustomCity.objects.create(
        name=name,
        country=country,
        region=region,
        subregion=subregion,
        pin_code=pin_code,
        timezone=timezone,
        created_by=None,
        updated_by=None
    )

def create_test_global_region(name=None):
    """Create a test GlobalRegion."""
    if name is None:
        name = f'Test Global Region {uuid.uuid4().hex[:8]}'
    return GlobalRegion.objects.create(
        name=name,
        created_by=None,
        updated_by=None
    )

def create_test_timezone(display_name=None, timezone_id=None, gmt_offset_jan=0.0, dst_offset_jul=0.0, raw_offset=0.0, country_code='TC'):
    """Create a test Timezone."""
    if display_name is None:
        display_name = f'Test Timezone {uuid.uuid4().hex[:8]}'
    if timezone_id is None:
        timezone_id = f'Test/TZ{uuid.uuid4().hex[:8]}'
    return Timezone.objects.create(
        display_name=display_name,
        timezone_id=timezone_id,
        gmt_offset_jan=gmt_offset_jan,
        dst_offset_jul=dst_offset_jul,
        raw_offset=raw_offset,
        country_code=country_code,
        is_active=True,
        created_by=None,
        updated_by=None
    )

def create_test_location(city=None, postal_code='TKCA 1ZZ', user=None):
    """Create a test Location."""
    if city is None:
        city = create_test_city()
    return Location.objects.create(
        city=city,
        postal_code=postal_code,
        created_by=user,
        updated_by=user
    )
