from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from locations.models import City, Country, GlobalRegion, State

from clients.models import Client, ClientOrganization, Industry, Organization
from clients.serializers import ClientOrganizationCreateSerializer, ClientSerializer, OrganizationSerializer


class ClientModelsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Ensure unique GlobalRegion creation
        global_region1, _ = GlobalRegion.objects.get_or_create(name="North America")
        global_region2, _ = GlobalRegion.objects.get_or_create(name="South Asia")

        country1, _ = Country.objects.get_or_create(
            name="United States", code="US", global_region=global_region1, location_type='country'
        )
        country2, _ = Country.objects.get_or_create(
            name="India", code="IN", global_region=global_region2, location_type='country'
        )

        state1, _ = State.objects.get_or_create(
            name="New York", country=country1, location_type='state'
        )
        state2, _ = State.objects.get_or_create(
            name="California", country=country1, location_type='state'
        )

        city1, _ = City.objects.get_or_create(
            name="New York City",
            country=country1,
            state=state1,
            defaults={
                'postal_code': "10001",
                'location_type': 'city'
            }
        )
        city2, _ = City.objects.get_or_create(
            name="San Francisco",
            country=country1,
            state=state2,
            defaults={
                'postal_code': "94105",
                'location_type': 'city'
            }
        )

        industry1, _ = Industry.objects.get_or_create(
            name="Tech", global_region=global_region1
        )
        industry2, _ = Industry.objects.get_or_create(
            name="Finance", global_region=global_region1
        )

        org1, _ = Organization.objects.get_or_create(
            name="Tech Corp", industry=industry1, headquarter_city=city1, created_by=None, updated_by=None
        )
        org1.cities.add(city1, city2)

        org2, _ = Organization.objects.get_or_create(
            name="FinCorp", industry=industry2, headquarter_city=city2, created_by=None, updated_by=None
        )
        org2.cities.add(city1, city2)

        client1, _ = Client.objects.get_or_create(
            name="John Doe",
            email="john.doe@example.com",
            defaults={
                'phone': "+1234567890",
                'current_organization': org1,
                'current_industry': industry1,
                'current_org_city': city2,
                'current_org_joining_day': timezone.now().date(),
                'current_country': country1,
                'current_state': state1,
                'current_region': global_region1,
                'created_by': None,
                'updated_by': None
            }
        )

        client2, _ = Client.objects.get_or_create(
            name="Jane Smith",
            email="jane.smith@example.com",
            defaults={
                'phone': "+0987654321",
                'current_organization': org2,
                'current_industry': industry2,
                'current_org_city': city1,
                'current_org_joining_day': timezone.now().date(),
                'current_country': country1,
                'current_state': state2,
                'current_region': global_region1,
                'created_by': None,
                'updated_by': None
            }
        )

        cls.data = {
            'client1': client1,
            'client2': client2,
            'org1': org1,
            'org2': org2,
            'city1': city1,
            'city2': city2,
            'industry1': industry1,
            'industry2': industry2,
            'country1': country1,
            'country2': country2,
            'state1': state1,
            'state2': state2,
            'global_region1': global_region1,
            'global_region2': global_region2
        }

    def test_industry_unique_constraint(self):
        with self.assertRaises(IntegrityError):
            Industry.objects.create(name=self.data['industry1'].name, global_region=self.data['global_region1'])

    def test_industry_str(self):
        self.assertEqual(str(self.data['industry1']), "Tech")

    def test_organization_create_valid(self):
        org = Organization.objects.create(
            name="New Org",
            industry=self.data['industry1'],
            headquarter_city=self.data['city1'],
            created_by=None,
            updated_by=None
        )
        org.cities.add(self.data['city1'])
        self.assertEqual(org.name, "New Org")

    def test_organization_headquarter_city_validation(self):
        org = Organization(
            name="Invalid Org",
            industry=self.data['industry1'],
            headquarter_city=self.data['city1'],
            created_by=None,
            updated_by=None
        )
        org.save()
        with self.assertRaises(ValidationError):
            org.cities.clear()
            org.clean()

    def test_organization_str(self):
        self.assertEqual(str(self.data['org1']), "Tech Corp")

    def test_create_client_invalid_industry(self):
        client = Client(
            name="Mismatch Industry",
            email="mismatch@example.com",
            phone="+1234567890",
            current_organization=self.data['org1'],
            current_industry=self.data['industry2'],
            current_org_city=self.data['city2'],
            current_country=self.data['country1'],
            current_state=self.data['state1'],
            current_region=self.data['global_region1'],
            created_by=None,
            updated_by=None
        )
        with self.assertRaises(ValidationError):
            client.clean()

    def test_create_client_invalid_city(self):
        new_city, _ = City.objects.get_or_create(
            name="Invalid City",
            country=self.data['country1'],
            state=self.data['state1'],
            postal_code="12345",
            location_type='city',
            defaults={'location_type': 'city'}
        )
        client = Client(
            name="Invalid City Client",
            email="invalid.city@example.com",
            phone="+1234567890",
            current_organization=self.data['org1'],
            current_industry=self.data['industry1'],
            current_org_city=new_city,
            current_country=self.data['country1'],
            current_state=self.data['state1'],
            current_region=self.data['global_region1'],
            created_by=None,
            updated_by=None
        )
        with self.assertRaises(ValidationError):
            client.clean()

    def test_client_deactivation(self):
        client = self.data['client1']
        client.is_active = False
        client.save()
        self.assertIsNotNone(client.deleted_at)

    def test_client_reactivation(self):
        client = self.data['client1']
        client.is_active = False
        client.save()
        client.is_active = True
        client.save()
        self.assertIsNone(client.deleted_at)

    def test_client_str(self):
        self.assertEqual(str(self.data['client1']), "John Doe")

    def test_client_organization_invalid_dates(self):
        client_org = ClientOrganization(
            client=self.data['client1'],
            organization=self.data['org1'],
            from_date=timezone.now().date(),
            to_date=timezone.now().date() - timezone.timedelta(days=1),
            corporate_affiliation_city=self.data['city2']
        )
        with self.assertRaises(ValidationError):
            client_org.full_clean()

    def test_client_organization_unique_constraint(self):
        ClientOrganization.objects.create(
            client=self.data['client1'],
            organization=self.data['org1'],
            from_date=timezone.now().date(),
            corporate_affiliation_city=self.data['city2']
        )
        with self.assertRaises(IntegrityError):
            ClientOrganization.objects.create(
                client=self.data['client1'],
                organization=self.data['org1'],
                from_date=timezone.now().date(),
                corporate_affiliation_city=self.data['city2']
            )

    def test_client_organization_str(self):
        client_org = ClientOrganization.objects.create(
            client=self.data['client1'],
            organization=self.data['org1'],
            from_date=timezone.now().date(),
            corporate_affiliation_city=self.data['city2']
        )
        self.assertEqual(str(client_org), "John Doe - Tech Corp")

    def test_client_serializer(self):
        serializer = ClientSerializer(self.data['client1'])
        self.assertEqual(serializer.data['name'], self.data['client1'].name)
        self.assertEqual(serializer.data['email'], self.data['client1'].email)
        self.assertEqual(serializer.data['current_organization'], self.data['client1'].current_organization.id)

    def test_organization_serializer(self):
        serializer = OrganizationSerializer(self.data['org1'])
        self.assertEqual(serializer.data['name'], self.data['org1'].name)
        self.assertEqual(serializer.data['industry'], self.data['org1'].industry.id)
        self.assertEqual(serializer.data['headquarter_city'], self.data['org1'].headquarter_city.id)

    def test_client_organization_serializer(self):
        client_org = ClientOrganization.objects.create(
            client=self.data['client1'],
            organization=self.data['org1'],
            from_date=timezone.now().date(),
            to_date=timezone.now().date(),
            corporate_affiliation_city=self.data['city2']
        )
        serializer = ClientOrganizationCreateSerializer(client_org)
        self.assertEqual(serializer.data['client'], self.data['client1'].id)
        self.assertEqual(serializer.data['organization'], self.data['org1'].id)
        self.assertEqual(serializer.data['corporate_affiliation_city'], self.data['city2'].id)

    def test_client_invalid_state_country(self):
        client = Client(
            name="Invalid State Country",
            email="invalid.state@example.com",
            phone="+1234567890",
            current_organization=self.data['org1'],
            current_industry=self.data['industry1'],
            current_org_city=self.data['city2'],
            current_country=self.data['country2'],
            current_state=self.data['state1'],
            current_region=self.data['global_region1'],
            created_by=None,
            updated_by=None
        )
        with self.assertRaises(ValidationError):
            client.clean()

    def test_active_manager(self):
        self.data['client1'].is_active = False
        self.data['client1'].save()
        active_clients = Client.objects.all()
        self.assertNotIn(self.data['client1'], active_clients)
        self.assertIn(self.data['client2'], active_clients)

    def test_all_objects_manager(self):
        self.data['client1'].is_active = False
        self.data['client1'].save()
        all_clients = Client.all_objects.all()
        self.assertIn(self.data['client1'], all_clients)
        self.assertIn(self.data['client2'], all_clients)
