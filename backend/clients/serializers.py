import phonenumbers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.utils import timezone
from phonenumbers import is_valid_number, parse
from rest_framework import serializers

from .models import City, Client, ClientOrganization, Industry, Organization


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ['id', 'name']


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'city']


class OrganizationSerializer(serializers.ModelSerializer):
    industry = serializers.PrimaryKeyRelatedField(queryset=Industry.objects.all(), required=True)
    current_org_head_office = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)
    current_org_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Organization
        fields = ['id', 'name', 'industry', 'current_org_head_office', 'current_org_city']

    def validate_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Organization name must be at least 3 characters")
        return value


class ClientBaseSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Client name must be at least 3 characters.")
        return value

    def validate_email(self, value):
        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Invalid email format.")
        return value

    def validate_phone(self, value):
        try:
            phone = parse(value, region='IN')
            if not is_valid_number(phone):
                raise serializers.ValidationError("Invalid phone number.")
        except phonenumbers.phonenumberutil.NumberParseException:
            raise serializers.ValidationError("Invalid phone number format.")
        return value

    def validate_current_org_joining_day(self, value):
        if value and value > timezone.now():
            raise serializers.ValidationError("Joining date cannot be in the future.")
        return value

    class Meta:
        model = Client
        fields = [
            'id', 'name', 'email', 'phone', 'current_organization',
            'current_org_city', 'industry', 'current_org_joining_day',
            'current_country', 'current_state', 'current_region', 'other_orgs',
        ]


class ClientSerializer(ClientBaseSerializer):
    current_organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=False, allow_null=True)
    industry = serializers.PrimaryKeyRelatedField(queryset=Industry.objects.all(), required=False, allow_null=True)
    current_org_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)
    other_orgs = OrganizationSerializer(many=True, read_only=True)

    class Meta(ClientBaseSerializer.Meta):
        model = Client
        fields = ClientBaseSerializer.Meta.fields


class ClientCreateSerializer(ClientBaseSerializer):
    def validate(self, data):
        current_organization = data.get('current_organization')
        industry = data.get('industry')

        if current_organization and not industry:
            raise serializers.ValidationError("Industry must be provided if a current organization is specified.")

        if current_organization and industry and current_organization.industry != industry:
            raise serializers.ValidationError("Industry does not match the current organization's industry.")

        return data

    def create(self, validated_data):
        if 'current_org_joining_day' not in validated_data or not validated_data['current_org_joining_day']:
            validated_data['current_org_joining_day'] = timezone.now().date()

        client = Client.objects.create(**validated_data)

        current_organization = validated_data.get('current_organization')
        if current_organization:
            client.other_orgs.add(current_organization)
        return client


class ClientInvoicePurposeSerializer(ClientBaseSerializer):
    class Meta(ClientBaseSerializer.Meta):
        fields = ['id', 'name', 'email']


class ClientOrganizationCreateSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=True)
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=True)
    corporate_affiliation_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)

    def validate(self, data):
        if data['from_date'] and data['to_date'] and data['from_date'] > data['to_date']:
            raise serializers.ValidationError("from_date cannot be after to_date.")
        return data

    class Meta:
        model = ClientOrganization
        fields = ['client', 'organization', 'from_date', 'to_date', 'corporate_affiliation_city']


class ClientOrganizationReadSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    corporate_affiliation_city = CitySerializer(read_only=True)

    class Meta:
        model = ClientOrganization
        fields = ['client', 'organization', 'from_date', 'to_date', 'corporate_affiliation_city']


class OrganizationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['name', 'industry', 'current_org_head_office', 'current_org_city']

    def validate_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Organization name must be at least 3 characters.")
        return value

    def validate(self, data):
        if not data.get('industry'):
            raise serializers.ValidationError("Industry is required.")
        if not data.get('current_org_head_office'):
            raise serializers.ValidationError("Head office city is required.")
        if not data.get('current_org_city'):
            raise serializers.ValidationError("Current workplace city is required.")
        return data
