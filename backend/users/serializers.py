import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import User


class CustomPasswordValidator:
    def __call__(self, password, user=None):
        validate_password(password, user)
        regex = r"^(?=.*[A-Z])(?=.*\d)(?=.*[!@$%^&*()_+={}[\]|\:;\"'<>,.?/\\\-]).{8,32}$"
        if not re.match(regex, password):
            raise serializers.ValidationError(
                "Password must be 8-32 characters, with an uppercase letter, number, and special character."
            )

class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all()), validate_email]
    )
    password = serializers.CharField(write_only=True, validators=[CustomPasswordValidator()])
    username = serializers.CharField(required=False, validators=[UniqueValidator(queryset=User.objects.all())])
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False, default=True)
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()

    def get_created_by(self, obj):
        return obj.created_by.username if obj.created_by else "Deleted User"

    def get_updated_by(self, obj):
        return obj.updated_by.username if obj.updated_by else "Deleted User"

    class Meta:
        model = User
        fields = [
            'id', 'employee_code', 'username', 'password', 'email', 'first_name', 'last_name',
            'department', 'role', 'approval_limit', 'phone_number', 'job_title', 'region', 'timezone',
            'avatar', 'is_active', 'created_by', 'updated_by'
        ]
        read_only_fields = ['id', 'employee_code', 'created_by', 'updated_by']

    def validate_email(self, value):
        allowed_domains = ("djp.com", "gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "test.com", "ex.com", "example.com")
        domain = value.split('@')[1]
        if domain not in allowed_domains:
            raise serializers.ValidationError(f"Email domain {domain} not allowed.")
        if User.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("Email already in use.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as err:
            raise serializers.ValidationError(f"Password does not meet requirements: {err}") from err
        return value

    def validate_username(self, value):
        if value and User.objects.filter(username=value).exclude(
                id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("Username already in use.")
        return value

    def get_default_user(self):
        try:
            return User.objects.get(id=1)
        except User.DoesNotExist as err:
            raise serializers.ValidationError("No default user found.") from err

    def create(self, validated_data):
        user = self.context.get('request').user if self.context.get('request') and self.context.get('request').user.is_authenticated else self.get_default_user()
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        user_instance = User.objects.create_user(
            email=email,
            password=password,
            username=validated_data.get('username'),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            department=validated_data.get('department', 'OT'),
            role=validated_data.get('role', 'CLERK'),
            approval_limit=validated_data.get('approval_limit', 0.00),
            phone_number=validated_data.get('phone_number', ''),
            job_title=validated_data.get('job_title', ''),
            region=validated_data.get('region', ''),
            timezone=validated_data.get('timezone', 'IST'),
            avatar=validated_data.get('avatar', None),
            is_active=validated_data.get('is_active', True),
            created_by=user,
            updated_by=user
        )
        return user_instance

    def update(self, instance, validated_data):
        user = self.context.get('request').user if self.context.get('request') else self.get_default_user()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = user
        instance.save()
        return instance
