from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django_countries.fields import Country
from locations.models import City, Country, GlobalRegion, State

from .models import Client, ClientOrganization, Industry, Organization


class BaseTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create shared GlobalRegion and Country objects
        cls.global_region_asia, _ = GlobalRegion.objects.get_or_create(name="Asia")
        cls.global_region_na, _ = GlobalRegion.objects.get_or_create(name="North America")

        # Ensure countries are created only if they don't exist
        for code, name, region in [
            ('IN', "India", cls.global_region_asia),
            ('US', "United States", cls.global_region_na),
            ('GB', "United Kingdom", cls.global_region_na),
            ('JP', "Japan", cls.global_region_asia),
        ]:
            Country.objects.get_or_create(
                code=Country(code=code),
                defaults={'name': name, 'global_region': region}
            )

    def setUp(self):
        # Clear any instance-specific data to ensure test isolation
        self.global_region_asia = GlobalRegion.objects.get(name="Asia")
        self.global_region_na = GlobalRegion.objects.get(name="North America")
        self.country_in = Country.objects.get(code='IN')
        self.country_us = Country.objects.get(code='US')
        self.country_uk = Country.objects.get(code='GB')
        self.country_jp = Country.objects.get(code='JP')


class IndustryModelTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.industry, _ = Industry.objects.get_or_create(name="Technology")

    def test_industry_creation(self):
        """Test if Industry object is created correctly."""
        self.assertEqual(self.industry.name, "Technology")
        self.assertIsNotNone(self.industry.created_at)
        self.assertIsNone(self.industry.deleted_at)

    def test_industry_str(self):
        """Test the string representation of Industry."""
        self.assertEqual(str(self.industry), "Technology")

    def test_industry_unique_name(self):
        """Test that duplicate industry names are not allowed."""
        with self.assertRaises(Exception):
            Industry.objects.create(name="Technology")


class OrganizationModelTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.industry, _ = Industry.objects.get_or_create(name="Finance")
        self.state, _ = State.objects.get_or_create(name="Maharashtra", code="MH", country=self.country_in)
        self.city, _ = City.objects.get_or_create(
            country=self.country_in,
            state=self.state,
            city="Pune",
            postal_code="411001"
        )
        self.organization, _ = Organization.objects.get_or_create(
            name="Tech Corp",
            industry=self.industry,
            current_org_head_office=self.city,
            current_org_city=self.city
        )

    def test_organization_creation(self):
        """Test if Organization object is created correctly."""
        self.assertEqual(self.organization.name, "Tech Corp")
        self.assertEqual(self.organization.industry.name, "Finance")
        self.assertEqual(self.organization.current_org_head_office.city, "Pune")
        self.assertEqual(self.organization.current_org_city.city, "Pune")
        self.assertIsNotNone(self.organization.created_at)
        self.assertIsNone(self.organization.deleted_at)

    def test_organization_str(self):
        """Test the string representation of Organization."""
        self.assertEqual(str(self.organization), "Tech Corp")

    def test_organization_without_industry(self):
        """Test organization creation without an industry."""
        org, _ = Organization.objects.get_or_create(
            name="No Industry Corp",
            current_org_head_office=self.city,
            current_org_city=self.city
        )
        self.assertIsNone(org.industry)


class ClientModelTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.industry, _ = Industry.objects.get_or_create(name="Healthcare")
        self.state, _ = State.objects.get_or_create(name="Maharashtra", code="MH", country=self.country_in)
        self.city, _ = City.objects.get_or_create(
            country=self.country_in,
            state=self.state,
            city="Mumbai",
            postal_code="400001"
        )
        self.organization, _ = Organization.objects.get_or_create(
            name="Health Corp",
            industry=self.industry,
            current_org_head_office=self.city,
            current_org_city=self.city
        )
        self.client, _ = Client.objects.get_or_create(
            name="Shekhar Bhosale",
            email="shekhar@paystream.com",
            phone="+919876543210",
            current_organization=self.organization,
            current_org_city=self.city,
            current_country=self.country_in,
            current_state=self.state,
            current_region=self.global_region_asia,
            industry=self.industry,
            current_org_joining_day=date(2023, 1, 1)
        )

    def test_client_creation(self):
        """Test if Client object is created correctly."""
        self.assertEqual(self.client.name, "Shekhar Bhosale")
        self.assertEqual(self.client.email, "shekhar@paystream.com")
        self.assertEqual(self.client.phone, "+919876543210")
        self.assertEqual(self.client.current_organization.name, "Health Corp")
        self.assertEqual(self.client.current_org_city.city, "Mumbai")
        self.assertEqual(self.client.current_country.name, "India")
        self.assertEqual(self.client.current_state.name, "Maharashtra")
        self.assertEqual(self.client.current_region.name, "Asia")
        self.assertEqual(self.client.industry.name, "Healthcare")
        self.assertEqual(self.client.current_org_joining_day, date(2023, 1, 1))
        self.assertIsNotNone(self.client.created_at)
        self.assertIsNone(self.client.deleted_at)

    def test_client_str(self):
        """Test the string representation of Client."""
        self.assertEqual(str(self.client), "Shekhar Bhosale")

    def test_client_unique_email(self):
        """Test that duplicate client emails are not allowed."""
        with self.assertRaises(Exception):
            Client.objects.create(
                name="Another Client",
                email="shekhar@paystream.com",
                current_org_city=self.city
            )

    def test_client_without_organization(self):
        """Test client creation without an organization."""
        client, _ = Client.objects.get_or_create(
            name="Independent Client",
            email="independent@paystream.com",
            current_org_city=self.city
        )
        self.assertIsNone(client.current_organization)


class ClientOrganizationModelTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.industry, _ = Industry.objects.get_or_create(name="Technology")
        self.state, _ = State.objects.get_or_create(name="Delhi", code="DL", country=self.country_in)
        self.city, _ = City.objects.get_or_create(
            country=self.country_in,
            state=self.state,
            city="Delhi",
            postal_code="110001"
        )
        self.organization, _ = Organization.objects.get_or_create(
            name="Tech Inc.",
            industry=self.industry,
            current_org_head_office=self.city,
            current_org_city=self.city
        )
        self.client, _ = Client.objects.get_or_create(
            name="Shekhar Bhosale",
            email="shekhar@paystream.com",
            current_org_city=self.city
        )
        self.client_org, _ = ClientOrganization.objects.get_or_create(
            client=self.client,
            organization=self.organization,
            from_date=date(2021, 1, 1),
            to_date=date(2022, 1, 1),
            corporate_affiliation_city=self.city
        )

    def test_client_organization_creation(self):
        """Test if ClientOrganization object is created correctly."""
        self.assertEqual(self.client_org.client.name, "Shekhar Bhosale")
        self.assertEqual(self.client_org.organization.name, "Tech Inc.")
        self.assertEqual(self.client_org.from_date, date(2021, 1, 1))
        self.assertEqual(self.client_org.to_date, date(2022, 1, 1))
        self.assertEqual(self.client_org.corporate_affiliation_city.city, "Delhi")

    def test_client_organization_str(self):
        """Test the string representation of ClientOrganization."""
        self.assertEqual(str(self.client_org), "Shekhar Bhosale - Tech Inc.")

    def test_client_organization_unique_together(self):
        """Test unique_together constraint on client, organization, and from_date."""
        with self.assertRaises(Exception):
            ClientOrganization.objects.create(
                client=self.client,
                organization=self.organization,
                from_date=date(2021, 1, 1),
                corporate_affiliation_city=self.city
            )


class SoftDeleteTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.industry, _ = Industry.objects.get_or_create(name="Retail")
        self.state, _ = State.objects.get_or_create(name="Tokyo", code="TK", country=self.country_jp)
        self.city, _ = City.objects.get_or_create(
            country=self.country_jp,
            state=self.state,
            city="Tokyo",
            postal_code="100-0001"
        )
        self.organization, _ = Organization.objects.get_or_create(
            name="Retail Corp",
            industry=self.industry,
            current_org_head_office=self.city,
            current_org_city=self.city
        )

    def test_soft_delete(self):
        """Test if soft delete works correctly."""
        self.organization.soft_delete()
        self.organization.refresh_from_db()
        self.assertIsNotNone(self.organization.deleted_at)

    def test_restore(self):
        """Test if restore works correctly."""
        self.organization.soft_delete()
        self.organization.restore()
        self.organization.refresh_from_db()
        self.assertIsNone(self.organization.deleted_at)


class ActiveManagerTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.industry, _ = Industry.objects.get_or_create(name="Tech")
        self.state, _ = State.objects.get_or_create(name="Osaka", code="OS", country=self.country_jp)
        self.city, _ = City.objects.get_or_create(
            country=self.country_jp,
            state=self.state,
            city="Osaka",
            postal_code="530-0001"
        )
        self.active_org, _ = Organization.objects.get_or_create(
            name="Active Org",
            industry=self.industry,
            current_org_head_office=self.city,
            current_org_city=self.city
        )
        self.deleted_org, _ = Organization.objects.get_or_create(
            name="Deleted Org",
            industry=self.industry,
            current_org_head_office=self.city,
            current_org_city=self.city
        )
        self.deleted_org.soft_delete()

    def test_active_manager(self):
        """Test if ActiveManager filters out soft-deleted records."""
        active_organizations = Organization.objects.all()
        self.assertIn(self.active_org, active_organizations)
        self.assertNotIn(self.deleted_org, active_organizations)

    def test_all_objects_manager(self):
        """Test if all_objects manager includes soft-deleted records."""
        all_organizations = Organization.all_objects.all()
        self.assertIn(self.active_org, all_organizations)
        self.assertIn(self.deleted_org, all_organizations)


class CityModelValidationTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.state_ca, _ = State.objects.get_or_create(name="California", code="CA", country=self.country_us)
        self.state_ny, _ = State.objects.get_or_create(name="New York", code="NY", country=self.country_us)

    def test_valid_us_postal_code(self):
        """Test valid US postal code formats."""
        city, _ = City.objects.get_or_create(
            country=self.country_us,
            state=self.state_ca,
            city="San Francisco",
            postal_code="94105"
        )
        self.assertEqual(city.postal_code, "94105")

    def test_invalid_us_postal_code(self):
        """Test invalid US postal code format."""
        with self.assertRaises(ValidationError):
            city = City(
                country=self.country_us,
                state=self.state_ca,
                city="San Francisco",
                postal_code="123"
            )
            city.full_clean()

    def test_valid_uk_postal_code(self):
        """Test valid UK postal code format."""
        city, _ = City.objects.get_or_create(
            country=self.country_uk,
            city="London",
            postal_code="SW1A 1AA"
        )
        self.assertEqual(city.postal_code, "SW1A 1AA")

    def test_state_country_mismatch(self):
        """Test validation for state-country mismatch."""
        with self.assertRaises(ValidationError):
            city = City(
                country=self.country_uk,
                state=self.state_ca,  # California does not belong to UK
                city="London"
            )
            city.full_clean()
