from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import TestCase

from locations.models import CustomCity, CustomCountry, CustomRegion, CustomSubRegion, GlobalRegion, Location, Timezone
from locations.tests.test_utils import *


class CustomCountryModelTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.country = create_test_country()

    def tearDown(self):
        try:
            with transaction.atomic():
                CustomCountry.objects.all().delete()
        except transaction.TransactionManagementError:
            transaction.set_rollback(True)

    def test_country_creation(self):
        """Test creating a CustomCountry."""
        country = create_test_country()
        self.assertTrue(isinstance(country, CustomCountry))
        self.assertEqual(country.name, country.name)
        self.assertEqual(country.country_code, 'TC')

    def test_country_unique_name(self):
        """Test that CustomCountry names must be unique."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_test_country(name=self.country.name)

    def test_country_invalid_country_code(self):
        """Test validation of country code (2 characters)."""
        with self.assertRaises(ValidationError):
            create_test_country(country_code='T')

    def test_country_soft_delete(self):
        """Test soft deleting a CustomCountry."""
        self.country.soft_delete(user=self.user)
        self.assertIsNotNone(self.country.deleted_at)
        self.assertFalse(self.country.is_active)
        self.assertEqual(self.country.deleted_by, self.user)

    def test_country_restore(self):
        """Test restoring a soft-deleted CustomCountry."""
        self.country.soft_delete(user=self.user)
        self.country.restore(user=self.user)
        self.assertIsNone(self.country.deleted_at)
        self.assertTrue(self.country.is_active)
        self.assertIsNone(self.country.deleted_by)

class CustomRegionModelTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.country = create_test_country()
        self.region = create_test_region(country=self.country)

    def tearDown(self):
        try:
            with transaction.atomic():
                CustomRegion.objects.all().delete()
                CustomCountry.objects.all().delete()
        except transaction.TransactionManagementError:
            transaction.set_rollback(True)

    def test_region_creation(self):
        """Test creating a CustomRegion."""
        region = create_test_region(country=self.country)
        self.assertTrue(isinstance(region, CustomRegion))
        self.assertEqual(region.country, self.country)

    def test_region_unique_name_per_country(self):
        """Test that CustomRegion names must be unique per country."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_test_region(name=self.region.name, country=self.country)

    def test_region_invalid_code(self):
        """Test validation of region code (alphanumeric with hyphens, max 10 chars)."""
        with self.assertRaises(ValidationError):
            create_test_region(country=self.country, code='INVALID@')

    def test_region_soft_delete(self):
        """Test soft deleting a CustomRegion."""
        self.region.soft_delete(user=self.user)
        self.assertIsNotNone(self.region.deleted_at)
        self.assertFalse(self.region.is_active)
        self.assertEqual(self.region.deleted_by, self.user)

    def test_region_restore(self):
        """Test restoring a soft-deleted CustomRegion."""
        self.region.soft_delete(user=self.user)
        self.region.restore(user=self.user)
        self.assertIsNone(self.region.deleted_at)
        self.assertTrue(self.region.is_active)
        self.assertIsNone(self.region.deleted_by)

class CustomSubRegionModelTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.country = create_test_country()
        self.region = create_test_region(country=self.country)
        self.subregion = create_test_subregion(region=self.region)

    def tearDown(self):
        try:
            with transaction.atomic():
                CustomSubRegion.objects.all().delete()
                CustomRegion.objects.all().delete()
                CustomCountry.objects.all().delete()
        except transaction.TransactionManagementError:
            transaction.set_rollback(True)

    def test_subregion_creation(self):
        """Test creating a CustomSubRegion."""
        subregion = create_test_subregion(region=self.region)
        self.assertTrue(isinstance(subregion, CustomSubRegion))
        self.assertEqual(subregion.region, self.region)

    def test_subregion_unique_name_per_region(self):
        """Test that CustomSubRegion names must be unique per region."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_test_subregion(name=self.subregion.name, region=self.region)

    def test_subregion_invalid_code(self):
        """Test validation of subregion code (alphanumeric with hyphens, max 10 chars)."""
        with self.assertRaises(ValidationError):
            create_test_subregion(region=self.region, code='INVALID@')

    def test_subregion_soft_delete(self):
        """Test soft deleting a CustomSubRegion."""
        self.subregion.soft_delete(user=self.user)
        self.assertIsNotNone(self.subregion.deleted_at)
        self.assertFalse(self.subregion.is_active)
        self.assertEqual(self.subregion.deleted_by, self.user)

    def test_subregion_restore(self):
        """Test restoring a soft-deleted CustomSubRegion."""
        self.subregion.soft_delete(user=self.user)
        self.subregion.restore(user=self.user)
        self.assertIsNone(self.subregion.deleted_at)
        self.assertTrue(self.subregion.is_active)
        self.assertIsNone(self.subregion.deleted_by)

class CustomCityModelTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.country = create_test_country()
        self.region = create_test_region(country=self.country)
        self.subregion = create_test_subregion(region=self.region)
        self.timezone = create_test_timezone(country_code=self.country.country_code)
        self.city = create_test_city(
            country=self.country,
            region=self.region,
            subregion=self.subregion,
            timezone=self.timezone,
            pin_code='TKCA 1ZZ'
        )

    def tearDown(self):
        try:
            with transaction.atomic():
                CustomCity.objects.all().delete()
                CustomSubRegion.objects.all().delete()
                CustomRegion.objects.all().delete()
                CustomCountry.objects.all().delete()
                Timezone.objects.all().delete()
        except transaction.TransactionManagementError:
            transaction.set_rollback(True)

    def test_city_creation(self):
        """Test creating a CustomCity."""
        city = create_test_city(country=self.country, region=self.region, subregion=self.subregion, pin_code='TKCA 1ZZ')
        self.assertTrue(isinstance(city, CustomCity))
        self.assertEqual(city.country, self.country)
        self.assertEqual(city.region, self.region)
        self.assertEqual(city.subregion, self.subregion)

    def test_city_unique_name_per_country_region_subregion(self):
        """Test that CustomCity names must be unique per country, region, and subregion."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_test_city(
                    name=self.city.name,
                    country=self.country,
                    region=self.region,
                    subregion=self.subregion,
                    pin_code='TKCA 1ZZ'
                )

    def test_city_invalid_postal_code(self):
        """Test validation of postal code."""
        with self.assertRaises(ValidationError):
            create_test_city(country=self.country, pin_code='INVALID')

    def test_city_subregion_without_region(self):
        """Test that a city cannot have a subregion without a region."""
        with self.assertRaises(ValidationError):
            create_test_city(country=self.country, subregion=self.subregion, region=None, pin_code='TKCA 1ZZ')

    def test_city_soft_delete(self):
        """Test soft deleting a CustomCity."""
        self.city.soft_delete(user=self.user)
        self.assertIsNotNone(self.city.deleted_at)
        self.assertFalse(self.city.is_active)
        self.assertEqual(self.city.deleted_by, self.user)

    def test_city_restore(self):
        """Test restoring a soft-deleted CustomCity."""
        self.city.soft_delete(user=self.user)
        self.city.restore(user=self.user)
        self.assertIsNone(self.city.deleted_at)
        self.assertTrue(self.city.is_active)
        self.assertIsNone(self.city.deleted_by)

class GlobalRegionModelTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.global_region = create_test_global_region()

    def tearDown(self):
        try:
            with transaction.atomic():
                GlobalRegion.objects.all().delete()
        except transaction.TransactionManagementError:
            transaction.set_rollback(True)

    def test_global_region_creation(self):
        """Test creating a GlobalRegion."""
        global_region = create_test_global_region()
        self.assertTrue(isinstance(global_region, GlobalRegion))
        self.assertEqual(global_region.name, global_region.name)

    def test_global_region_unique_name(self):
        """Test that GlobalRegion names must be unique."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_test_global_region(name=self.global_region.name)

    def test_global_region_soft_delete(self):
        """Test soft deleting a GlobalRegion."""
        self.global_region.soft_delete(user=self.user)
        self.assertIsNotNone(self.global_region.deleted_at)
        self.assertFalse(self.global_region.is_active)
        self.assertEqual(self.global_region.deleted_by, self.user)

    def test_global_region_restore(self):
        """Test restoring a soft-deleted GlobalRegion."""
        self.global_region.soft_delete(user=self.user)
        self.global_region.restore(user=self.user)
        self.assertIsNone(self.global_region.deleted_at)
        self.assertTrue(self.global_region.is_active)
        self.assertIsNone(self.global_region.deleted_by)

class TimezoneModelTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.country = create_test_country()
        self.timezone = create_test_timezone(country_code=self.country.country_code)

    def tearDown(self):
        try:
            with transaction.atomic():
                Timezone.objects.all().delete()
                CustomCountry.objects.all().delete()
        except transaction.TransactionManagementError:
            transaction.set_rollback(True)

    def test_timezone_creation(self):
        """Test creating a Timezone."""
        timezone = create_test_timezone(country_code=self.country.country_code)
        self.assertTrue(isinstance(timezone, Timezone))
        self.assertTrue(timezone.is_active)

    def test_timezone_unique_id(self):
        """Test that Timezone IDs must be unique."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_test_timezone(timezone_id=self.timezone.timezone_id, country_code=self.country.country_code)

    def test_timezone_invalid_offset(self):
        """Test validation of timezone offsets."""
        with self.assertRaises(ValidationError):
            create_test_timezone(gmt_offset_jan=15.0, country_code=self.country.country_code)

    def test_timezone_invalid_country_code(self):
        """Test validation of country code."""
        with self.assertRaises(ValidationError):
            create_test_timezone(country_code='XX')

    def test_timezone_soft_delete(self):
        """Test soft deleting a Timezone."""
        self.timezone.soft_delete(user=self.user)
        self.assertIsNotNone(self.timezone.deleted_at)
        self.assertFalse(self.timezone.is_active)
        self.assertEqual(self.timezone.deleted_by, self.user)

    def test_timezone_restore(self):
        """Test restoring a soft-deleted Timezone."""
        self.timezone.soft_delete(user=self.user)
        self.timezone.restore(user=self.user)
        self.assertIsNone(self.timezone.deleted_at)
        self.assertTrue(self.timezone.is_active)
        self.assertIsNone(self.timezone.deleted_by)

class LocationModelTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.country = create_test_country()
        self.region = create_test_region(country=self.country)
        self.subregion = create_test_subregion(region=self.region)
        self.timezone = create_test_timezone(country_code=self.country.country_code)
        self.city = create_test_city(
            country=self.country,
            region=self.region,
            subregion=self.subregion,
            timezone=self.timezone,
            pin_code='TKCA 1ZZ'
        )
        self.location = create_test_location(city=self.city, user=self.user)

    def tearDown(self):
        try:
            with transaction.atomic():
                Location.objects.all().delete()
                CustomCity.objects.all().delete()
                CustomSubRegion.objects.all().delete()
                CustomRegion.objects.all().delete()
                CustomCountry.objects.all().delete()
                Timezone.objects.all().delete()
        except transaction.TransactionManagementError:
            transaction.set_rollback(True)

    def test_location_creation(self):
        """Test creating a Location."""
        location = create_test_location(city=self.city, user=self.user)
        self.assertTrue(isinstance(location, Location))
        self.assertEqual(location.city, self.city)

    def test_location_unique_city_postal_code(self):
        """Test that Location city and postal code must be unique."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_test_location(city=self.city, postal_code=self.location.postal_code)

    def test_location_invalid_postal_code(self):
        """Test validation of postal code."""
        with self.assertRaises(ValidationError):
            create_test_location(city=self.city, postal_code='INVALID')

    def test_location_soft_delete(self):
        """Test soft deleting a Location."""
        self.location.soft_delete(user=self.user)
        self.assertIsNotNone(self.location.deleted_at)
        self.assertFalse(self.location.is_active)
        self.assertEqual(self.location.deleted_by, self.user)

    def test_location_restore(self):
        """Test restoring a soft-deleted Location."""
        self.location.soft_delete(user=self.user)
        self.location.restore(user=self.user)
        self.assertIsNone(self.location.deleted_at)
        self.assertTrue(self.location.is_active)
        self.assertIsNone(self.location.deleted_by)

    def test_add_or_get_location(self):
        """Test add_or_get_location method."""
        location = Location.add_or_get_location(
            city_name=self.city.name,
            country_name=self.country.name,
            region_name=self.region.name,
            subregion_name=self.subregion.name,
            postal_code='TKCA 1ZZ',
            user=self.user
        )
        self.assertTrue(isinstance(location, Location))
        self.assertEqual(location.city, self.city)
