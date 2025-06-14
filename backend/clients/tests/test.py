import pytest
from clients.models import Client, ClientOrganization, Industry, Organization
from clients.serializers import ClientOrganizationCreateSerializer, ClientSerializer, OrganizationSerializer
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from locations.models import City, Country, GlobalRegion, State


@pytest.fixture
def setup_data():
    """Fixture to create test data for models."""
    global_region1 = GlobalRegion.objects.create(name="North America")
    global_region2 = GlobalRegion.objects.create(name="South Asia")

    country1 = Country.objects.create(name="United States", code="US", global_region=global_region1, location_type='country')
    country2 = Country.objects.create(name="India", code="IN", global_region=global_region2, location_type='country')

    state1 = State.objects.create(name="New York", country=country1, location_type='state')
    state2 = State.objects.create(name="California", country=country1, location_type='state')

    city1 = City.objects.create(name="New York City", country=country1, state=state1, postal_code="10001", location_type='city')
    city2 = City.objects.create(name="San Francisco", country=country1, state=state2, postal_code="94105", location_type='city')

    industry1 = Industry.objects.create(name="Tech", global_region=global_region1)
    industry2 = Industry.objects.create(name="Finance", global_region=global_region1)

    org1 = Organization.objects.create(name="Tech Corp", industry=industry1, headquarter_city=city1)
    org1.cities.add(city1, city2)
    org2 = Organization.objects.create(name="FinCorp", industry=industry2, headquarter_city=city2)
    org2.cities.add(city1, city2)

    client1 = Client.objects.create(
        name="John Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        current_organization=org1,
        current_industry=industry1,
        current_org_city=city2,
        current_org_joining_day=timezone.now().date(),
        current_country=country1,
        current_state=state1,
        current_region=global_region1
    )

    client2 = Client.objects.create(
        name="Jane Smith",
        email="jane.smith@example.com",
        phone="+0987654321",
        current_organization=org2,
        current_industry=industry2,
        current_org_city=city1,
        current_org_joining_day=timezone.now().date(),
        current_country=country1,
        current_state=state2,
        current_region=global_region1
    )

    return {
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


# Industry Model Tests
@pytest.mark.django_db
def test_industry_unique_constraint(setup_data):
    """Test unique_together constraint on Industry model."""
    with pytest.raises(IntegrityError):
        Industry.objects.create(
            name=setup_data['industry1'].name,
            global_region=setup_data['global_region1']
        )


@pytest.mark.django_db
def test_industry_str(setup_data):
    """Test string representation of Industry model."""
    assert str(setup_data['industry1']) == "Tech"


# Organization Model Tests
@pytest.mark.django_db
def test_organization_create_valid(setup_data):
    """Test creating a valid organization."""
    org = Organization.objects.create(
        name="New Org",
        industry=setup_data['industry1'],
        headquarter_city=setup_data['city1']
    )
    org.cities.add(setup_data['city1'])
    assert org.name == "New Org"
    assert org.headquarter_city == setup_data['city1']


@pytest.mark.django_db
def test_organization_headquarter_city_validation(setup_data):
    """Test headquarter city must be in cities list."""
    org = Organization(
        name="Invalid Org",
        industry=setup_data['industry1'],
        headquarter_city=setup_data['city1']
    )
    org.save()
    org.cities.add(setup_data['city2'])  # Headquarter city not in cities
    with pytest.raises(ValidationError):
        org.clean()


@pytest.mark.django_db
def test_organization_str(setup_data):
    """Test string representation of Organization model."""
    assert str(setup_data['org1']) == "Tech Corp"


# Client Model Tests
@pytest.mark.django_db
def test_create_client_invalid_industry(setup_data):
    """Test creating a client with mismatched industry and organization."""
    client = Client(
        name="Bob Wilson",
        email="bob.wilson@example.com",
        current_organization=setup_data['org1'],
        current_industry=setup_data['industry2'],  # Mismatched industry
        current_org_city=setup_data['city2'],
        current_country=setup_data['country1'],
        current_state=setup_data['state1'],
        current_region=setup_data['global_region1']
    )
    with pytest.raises(ValidationError):
        client.clean()


@pytest.mark.django_db
def test_create_client_invalid_city(setup_data):
    """Test creating a client with city not in organization's cities."""
    client = Client(
        name="Bob Wilson",
        email="bob.wilson@example.com",
        current_organization=setup_data['org1'],
        current_industry=setup_data['industry1'],
        current_org_city=City.objects.create(
            name="Invalid City",
            country=setup_data['country1'],
            state=setup_data['state1'],
            postal_code="12345",
            location_type='city'
        ),
        current_country=setup_data['country1'],
        current_state=setup_data['state1'],
        current_region=setup_data['global_region1']
    )
    with pytest.raises(ValidationError):
        client.clean()


@pytest.mark.django_db
def test_client_deactivation(setup_data):
    """Test client deactivation sets deleted_at."""
    client = setup_data['client1']
    client.is_active = False
    client.save()
    assert client.deleted_at is not None


@pytest.mark.django_db
def test_client_reactivation(setup_data):
    """Test client reactivation clears deleted_at."""
    client = setup_data['client1']
    client.is_active = False
    client.save()
    client.is_active = True
    client.save()
    assert client.deleted_at is None


@pytest.mark.django_db
def test_client_str(setup_data):
    """Test string representation of Client model."""
    assert str(setup_data['client1']) == "John Doe"


# ClientOrganization Model Tests
@pytest.mark.django_db
def test_client_organization_invalid_dates(setup_data):
    """Test creating client-organization with invalid dates."""
    client_org = ClientOrganization(
        client=setup_data['client1'],
        organization=setup_data['org1'],
        from_date=timezone.now().date(),
        to_date=timezone.now().date() - timezone.timedelta(days=1),
        corporate_affiliation_city=setup_data['city2']
    )
    with pytest.raises(ValidationError):
        client_org.clean()


@pytest.mark.django_db
def test_client_organization_unique_constraint(setup_data):
    """Test unique_together constraint on ClientOrganization."""
    ClientOrganization.objects.create(
        client=setup_data['client1'],
        organization=setup_data['org1'],
        from_date=timezone.now().date(),
        corporate_affiliation_city=setup_data['city2']
    )
    with pytest.raises(IntegrityError):
        ClientOrganization.objects.create(
            client=setup_data['client1'],
            organization=setup_data['org1'],
            from_date=timezone.now().date(),
            corporate_affiliation_city=setup_data['city2']
        )


@pytest.mark.django_db
def test_client_organization_str(setup_data):
    """Test string representation of ClientOrganization model."""
    client_org = ClientOrganization.objects.create(
        client=setup_data['client1'],
        organization=setup_data['org1'],
        from_date=timezone.now().date(),
        corporate_affiliation_city=setup_data['city2']
    )
    assert str(client_org) == "John Doe - Tech Corp"


# Serializer Tests
@pytest.mark.django_db
def test_client_serializer(setup_data):
    """Test ClientSerializer serialization."""
    serializer = ClientSerializer(setup_data['client1'])
    assert serializer.data['name'] == setup_data['client1'].name
    assert serializer.data['email'] == setup_data['client1'].email
    assert serializer.data['current_organization'] == setup_data['client1'].current_organization.id


@pytest.mark.django_db
def test_organization_serializer(setup_data):
    """Test OrganizationSerializer serialization."""
    serializer = OrganizationSerializer(setup_data['org1'])
    assert serializer.data['name'] == setup_data['org1'].name
    assert serializer.data['industry'] == setup_data['org1'].industry.id
    assert serializer.data['headquarter_city'] == setup_data['org1'].headquarter_city.id


@pytest.mark.django_db
def test_client_organization_serializer(setup_data):
    """Test ClientOrganizationCreateSerializer serialization."""
    client_org = ClientOrganization.objects.create(
        client=setup_data['client1'],
        organization=setup_data['org1'],
        from_date=timezone.now().date(),
        to_date=timezone.now().date(),
        corporate_affiliation_city=setup_data['city2']
    )
    serializer = ClientOrganizationCreateSerializer(client_org)
    assert serializer.data['client'] == setup_data['client1'].id
    assert serializer.data['organization'] == setup_data['org1'].id
    assert serializer.data['corporate_affiliation_city'] == setup_data['city2'].id


# Additional Edge Case Tests
@pytest.mark.django_db
def test_client_invalid_state_country(setup_data):
    """Test creating a client with mismatched state and country."""
    client = Client(
        name="Bob Wilson",
        email="bob.wilson@example.com",
        current_organization=setup_data['org1'],
        current_industry=setup_data['industry1'],
        current_org_city=setup_data['city2'],
        current_country=setup_data['country2'],  # India
        current_state=setup_data['state1'],  # New York (US)
        current_region=setup_data['global_region1']
    )
    with pytest.raises(ValidationError):
        client.clean()


@pytest.mark.django_db
def test_active_manager(setup_data):
    """Test ActiveManager returns only active clients."""
    setup_data['client1'].is_active = False
    setup_data['client1'].save()
    active_clients = Client.objects.all()
    assert setup_data['client1'] not in active_clients
    assert setup_data['client2'] in active_clients


@pytest.mark.django_db
def test_all_objects_manager(setup_data):
    """Test all_objects manager returns all clients, including inactive."""
    setup_data['client1'].is_active = False
    setup_data['client1'].save()
    all_clients = Client.all_objects.all()
    assert setup_data['client1'] in all_clients
    assert setup_data['client2'] in all_clients
