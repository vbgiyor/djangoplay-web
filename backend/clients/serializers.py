import phonenumbers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.utils import timezone
from locations.models import City, Country, GlobalRegion, State, validate_postal_code
from phonenumbers import is_valid_number, parse
from rest_framework import serializers

from .models import Client, ClientOrganization, Industry, Organization


class IndustrySerializer(serializers.ModelSerializer):

    """Serializer for Industry model."""

    class Meta:
        model = Industry
        fields = ['id', 'name']

    def validate_name(self, value):
        """Ensure industry name is at least 3 characters."""
        if len(value) < 3:
            raise serializers.ValidationError("Industry name must be at least 3 characters.")
        return value


class CitySerializer(serializers.ModelSerializer):

    """Serializer for City model."""

    class Meta:
        model = City
        fields = ['id', 'name']


class OrganizationSerializer(serializers.ModelSerializer):

    """Serializer for Organization model with validation."""

    industry = serializers.PrimaryKeyRelatedField(queryset=Industry.objects.all(), required=True)
    headquarter_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=True)
    cities = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), many=True, required=False)

    class Meta:
        model = Organization
        fields = ['id', 'name', 'industry', 'headquarter_city', 'cities']

    def validate_name(self, value):
        """Ensure organization name is at least 3 characters."""
        if len(value) < 3:
            raise serializers.ValidationError("Organization name must be at least 3 characters.")
        return value

    def validate(self, data):
        """Validate headquarter city is in cities list."""
        headquarter_city = data.get('headquarter_city')
        cities = data.get('cities', [])
        if headquarter_city and headquarter_city not in cities:
            raise serializers.ValidationError("Headquarter city must be included in the list of cities.")
        return data


class ClientBaseSerializer(serializers.ModelSerializer):

    """Base serializer for Client model with common validations."""

    def validate_name(self, value):
        """Ensure client name is at least 3 characters."""
        if len(value) < 3:
            raise serializers.ValidationError("Client name must be at least 3 characters.")
        return value

    def validate_email(self, value):
        """Validate email format."""
        try:
            validate_email(value)
        except DjangoValidationError as err:
            raise serializers.ValidationError("Invalid email format.") from err
        return value

    def validate_phone(self, value):
        """Validate phone number format and validity."""
        if not value:
            return value
        country = self.initial_data.get('current_country')
        region = country.code if country else 'IN'
        try:
            phone = parse(value, region=region)
            if not is_valid_number(phone):
                raise serializers.ValidationError("Invalid phone number.")
        except phonenumbers.phonenumberutil.NumberParseException as err:
            raise serializers.ValidationError("Invalid phone number format.") from err
        return value

    def validate_current_org_joining_day(self, value):
        """Ensure joining date is not in the future."""
        if value and value > timezone.now().date():
            raise serializers.ValidationError("Joining date cannot be in the future.")
        return value

    class Meta:
        model = Client
        fields = [
            'id', 'name', 'email', 'phone', 'current_organization', 'current_org_city',
            'current_industry', 'current_org_joining_day', 'current_country',
            'current_region', 'current_state', 'other_organizations'
        ]


class ClientSerializer(ClientBaseSerializer):

    """Serializer for Client model with related field representations."""

    current_organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=False, allow_null=True)
    current_industry = serializers.PrimaryKeyRelatedField(queryset=Industry.objects.all(), required=False, allow_null=True)
    current_org_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)
    current_country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(), required=False, allow_null=True)
    current_region = serializers.PrimaryKeyRelatedField(queryset=GlobalRegion.objects.all(), required=False, allow_null=True)
    current_state = serializers.PrimaryKeyRelatedField(queryset=State.objects.all(), required=False, allow_null=True)
    other_organizations = OrganizationSerializer(many=True, read_only=True)

    class Meta(ClientBaseSerializer.Meta):
        pass


class ClientCreateSerializer(ClientBaseSerializer):

    """Serializer for creating Client instances with additional validations."""

    other_organizations = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), many=True, required=False)

    def validate(self, data):
        """Validate relationships and postal codes."""
        current_organization = data.get('current_organization')
        current_industry = data.get('current_industry')
        current_org_city = data.get('current_org_city')
        current_country = data.get('current_country')
        current_state = data.get('current_state')

        if current_organization and not current_industry:
            raise serializers.ValidationError("Industry must be provided if a current organization is specified.")
        if current_organization and current_industry and current_organization.industry != current_industry:
            raise serializers.ValidationError("Industry does not match the current organization's industry.")
        if current_organization and current_org_city and current_org_city not in current_organization.cities.all():
            raise serializers.ValidationError("Current organization city must be one of the organization's cities.")
        if current_state and current_country and current_state.country != current_country:
            raise serializers.ValidationError("Selected state does not belong to the selected country.")
        if current_org_city and current_org_city.postal_code:
            try:
                validate_postal_code(current_org_city.postal_code, current_org_city.country.code)
            except DjangoValidationError as err:
                raise serializers.ValidationError(f"Invalid postal code for {current_org_city.country.code}.") from err
        return data

    def create(self, validated_data):
        """Create Client instance and related ClientOrganization records."""
        other_organizations = validated_data.pop('other_organizations', [])
        if 'current_org_joining_day' not in validated_data or not validated_data['current_org_joining_day']:
            validated_data['current_org_joining_day'] = timezone.now().date()
        client = Client.objects.create(**validated_data)
        for org in other_organizations:
            ClientOrganization.objects.create(
                client=client, organization=org,
                from_date=validated_data.get('current_org_joining_day'),
                corporate_affiliation_city=validated_data.get('current_org_city')
            )
        return client


class ClientInvoicePurposeSerializer(ClientBaseSerializer):

    """Serializer for Client model tailored for invoice purposes."""

    current_organization = OrganizationSerializer(read_only=True)

    class Meta(ClientBaseSerializer.Meta):
        fields = ['id', 'name', 'email', 'current_organization']


class ClientOrganizationCreateSerializer(serializers.ModelSerializer):

    """Serializer for creating ClientOrganization instances."""

    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=True)
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=True)
    corporate_affiliation_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)

    def validate(self, data):
        """Validate date range and postal code."""
        if data['from_date'] and data['to_date'] and data['from_date'] > data['to_date']:
            raise serializers.ValidationError("from_date cannot be after to_date.")
        if data.get('corporate_affiliation_city') and data['corporate_affiliation_city'].postal_code:
            try:
                validate_postal_code(data['corporate_affiliation_city'].postal_code, data['corporate_affiliation_city'].country.code)
            except DjangoValidationError as err:
                raise serializers.ValidationError(f"Invalid postal code for {data['corporate_affiliation_city'].country.code}.") from err
        return data

    class Meta:
        model = ClientOrganization
        fields = ['client', 'organization', 'from_date', 'to_date', 'corporate_affiliation_city']


class ClientOrganizationReadSerializer(serializers.ModelSerializer):

    """Serializer for reading ClientOrganization instances with nested representations."""

    client = ClientSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    corporate_affiliation_city = CitySerializer(read_only=True)

    class Meta:
        model = ClientOrganization
        fields = ['client', 'organization', 'from_date', 'to_date', 'corporate_affiliation_city']


class OrganizationCreateSerializer(serializers.ModelSerializer):

    """Serializer for creating Organization instances."""

    class Meta:
        model = Organization
        fields = ['name', 'industry', 'headquarter_city', 'cities']

    def validate_name(self, value):
        """Ensure organization name is at least 3 characters."""
        if len(value) < 3:
            raise serializers.ValidationError("Organization name must be at least 3 characters.")
        return value

    def validate(self, data):
        """Validate industry, headquarter city, and postal code."""
        if not data.get('industry'):
            raise serializers.ValidationError("Industry is required.")
        if not data.get('headquarter_city'):
            raise serializers.ValidationError("Head office city is required.")
        headquarter_city = data.get('headquarter_city')
        cities = data.get('cities', [])
        if headquarter_city and headquarter_city not in cities:
            raise serializers.ValidationError("Headquarter city must be included in the list of cities.")
        if headquarter_city.postal_code:
            try:
                validate_postal_code(headquarter_city.postal_code, headquarter_city.country.code)
            except DjangoValidationError as err:
                raise serializers.ValidationError(f"Invalid postal code for {headquarter_city.country.code}.") from err
        return data


class ClientOrganizationUpdateSerializer(serializers.ModelSerializer):

    """Serializer for updating ClientOrganization instances."""

    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=True)
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=True)
    from_date = serializers.DateField(required=True)
    to_date = serializers.DateField(required=False, allow_null=True)
    corporate_affiliation_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)

    def validate(self, data):
        """Validate date range and postal code."""
        if data.get('from_date') and data.get('to_date') and data['from_date'] > data['to_date']:
            raise serializers.ValidationError("from_date cannot be after to_date.")
        if data.get('corporate_affiliation_city') and data['corporate_affiliation_city'].postal_code:
            try:
                validate_postal_code(data['corporate_affiliation_city'].postal_code, data['corporate_affiliation_city'].country.code)
            except DjangoValidationError as err:
                raise serializers.ValidationError(f"Invalid postal code for {data['corporate_affiliation_city'].country.code}.") from err
        return data

    class Meta:
        model = ClientOrganization
        fields = ['client', 'organization', 'from_date', 'to_date', 'corporate_affiliation_city']
