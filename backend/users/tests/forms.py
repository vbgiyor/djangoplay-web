import logging
import uuid
from decimal import Decimal

import phonenumbers
from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from users.constants import EMPLOYEE_TYPE_CODES
from users.models.employee import Address, User

logger = logging.getLogger(__name__)

class CustomUserChangeForm(UserChangeForm):
    current_address = forms.CharField(max_length=255, required=False, label="Current Address")
    permanent_address = forms.CharField(max_length=255, required=False, label="Permanent Address")
    country = forms.CharField(max_length=100, required=False, label="Country")
    state = forms.CharField(max_length=100, required=False, label="State/Region")
    city = forms.CharField(max_length=100, required=False, label="City")
    postal_code = forms.CharField(max_length=20, required=False, label="Postal Code")
    address_type = forms.CharField(max_length=50, required=False, label="Address Type")
    emergency_contact = forms.CharField(max_length=100, required=False, label="Emergency Contact")
    employee_type = forms.ChoiceField(choices=EMPLOYEE_TYPE_CODES, required=True, label="Employee Type")
    salary = forms.DecimalField(max_digits=10, decimal_places=2, required=False, label="Salary")
    termination_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Termination Date")
    created_by = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Created By",
        disabled=True
    )
    updated_by = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Updated By",
        disabled=True
    )

    class Meta:
        model = User
        fields = (
            'username', 'password', 'first_name', 'last_name', 'email', 'phone_number', 'job_title', 'avatar',
            'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',
            'department', 'role', 'approval_limit', 'manager', 'hire_date', 'employment_status',
            'employee_type', 'salary', 'termination_date',
            'current_address', 'permanent_address', 'country', 'state', 'city', 'postal_code',
            'address_type', 'emergency_contact'
        )

    def clean_postal_code(self):
        postal_code = self.cleaned_data.get('postal_code')
        if postal_code and not postal_code.strip():
            logger.debug("Cleaning postal_code: setting empty string to None")
            return None
        return postal_code

    def clean_termination_date(self):
        termination_date = self.cleaned_data.get('termination_date')
        if termination_date and termination_date > timezone.now().date():
            logger.error("Invalid termination date: Future date provided")
            raise forms.ValidationError('Termination date cannot be in the future.')
        if termination_date and self.cleaned_data.get('hire_date') and termination_date < self.cleaned_data.get('hire_date'):
            logger.error("Invalid termination date: Before hire date")
            raise forms.ValidationError('Termination date cannot be before hire date.')
        return termination_date

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number or not phone_number.strip():
            logger.debug(f"Cleaning phone_number for {self.cleaned_data.get('username', 'unknown')}: setting empty/None to None")
            return None
        if self.instance.pk and phone_number == self.instance.phone_number:
            logger.debug(f"Phone number unchanged for {self.cleaned_data.get('username', 'unknown')}: {phone_number}")
            return phone_number
        try:
            parsed = phonenumbers.parse(phone_number, None)
            if not phonenumbers.is_valid_number(parsed):
                logger.error(f"Phone number validation failed for {self.cleaned_data.get('username', 'unknown')}: {phone_number}")
                raise forms.ValidationError('Phone number must be a valid international number (e.g., +1234567890).')
            normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            logger.debug(f"Normalized phone number for {self.cleaned_data.get('username', 'unknown')}: {normalized}")
            return normalized
        except phonenumbers.NumberParseException:
            raise forms.ValidationError('Phone number must be in international format (e.g., +1234567890).')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            logger.info(f"Initializing form for user {self.instance.username}, address: {self.instance.address}")
            logger.debug(f"Created_by type: {type(self.instance.created_by)}, value: {self.instance.created_by}")
            if self.instance.address:
                address = self.instance.address
                self.fields['current_address'].initial = address.current_address or ''
                self.fields['permanent_address'].initial = address.permanent_address or ''
                self.fields['country'].initial = address.country or ''
                self.fields['state'].initial = address.state or ''
                self.fields['city'].initial = address.city or ''
                self.fields['postal_code'].initial = address.postal_code or ''
                self.fields['address_type'].initial = address.address_type or ''
                self.fields['emergency_contact'].initial = address.emergency_contact or ''
            if 'created_by' in self.fields:
                created_by = self.instance.created_by
                if isinstance(created_by, User):
                    self.fields['created_by'].initial = created_by
                else:
                    self.fields['created_by'].initial = None
                    logger.warning(f"Invalid created_by type for user {self.instance.username}: {type(created_by)}, value: {created_by}")
            if 'updated_by' in self.fields:
                updated_by = self.instance.updated_by
                if isinstance(updated_by, User):
                    self.fields['updated_by'].initial = updated_by
                else:
                    self.fields['updated_by'].initial = None
                    logger.warning(f"Invalid updated_by type for user {self.instance.username}: {type(updated_by)}, value: {updated_by}")

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk and getattr(self.instance, '_skip_full_clean', False):
            logger.debug(f"Skipping full clean for user {self.instance.username}")
            return cleaned_data
        postal_code = cleaned_data.get('postal_code')
        phone_number = cleaned_data.get('phone_number')
        if postal_code and not postal_code.strip():
            cleaned_data['postal_code'] = None
        if phone_number and not phone_number.strip():
            cleaned_data['phone_number'] = None
        return cleaned_data

    def save(self, commit=True, user=None):
        with transaction.atomic():
            logger.info(f"Saving CustomUserChangeForm for user: {self.cleaned_data.get('username')}, user={user}")
            user_instance = super().save(commit=False)
            address_data = {
                'current_address': self.cleaned_data.get('current_address', ''),
                'permanent_address': self.cleaned_data.get('permanent_address', ''),
                'country': self.cleaned_data.get('country', ''),
                'state': self.cleaned_data.get('state', ''),
                'city': self.cleaned_data.get('city', ''),
                'postal_code': self.cleaned_data.get('postal_code', ''),
                'address_type': self.cleaned_data.get('address_type', ''),
                'emergency_contact': self.cleaned_data.get('emergency_contact', ''),
            }
            logger.debug(f"Address data: {address_data}")

            if any(address_data.values()):
                logger.info(f"Non-empty address data provided for user: {user_instance.username}")
                if user_instance.address:
                    for key, value in address_data.items():
                        setattr(user_instance.address, key, value)
                    try:
                        user_instance.address.save(user=user)
                        logger.info(f"Updated address for user: {user_instance.username}, address_id: {user_instance.address.id}")
                    except Exception as e:
                        logger.error(f"Failed to update address for user {user_instance.username}: {e}", exc_info=True)
                        raise
                else:
                    try:
                        address = Address.objects.create(**address_data, created_by=user, updated_by=user)
                        user_instance.address = address
                        logger.info(f"Created new address for user: {user_instance.username}, address_id: {address.id}")
                    except Exception as e:
                        logger.error(f"Failed to create address for user {user_instance.username}: {e}", exc_info=True)
                        raise
            else:
                user_instance.address = None

            user_instance.employee_type = self.cleaned_data.get('employee_type')
            user_instance.salary = self.cleaned_data.get('salary')
            user_instance.termination_date = self.cleaned_data.get('termination_date')
            user_instance.phone_number = self.cleaned_data.get('phone_number')

            if commit:
                try:
                    user_instance.save(user=user or self.instance.updated_by or self.instance.created_by)
                    logger.info(f"User saved successfully: {user_instance.username}")
                    user_instance.groups.set(self.cleaned_data.get('groups', []))
                    user_instance.user_permissions.set(self.cleaned_data.get('user_permissions', []))
                    logger.info(f"Set groups and permissions for user: {user_instance.username}")
                except ValidationError as e:
                    logger.error(f"Validation error saving user {user_instance.username}: {e}", exc_info=True)
                    raise
                except Exception as e:
                    logger.error(f"Failed to save user {user_instance.username}: {e}", exc_info=True)
                    raise

            return user_instance

class CustomUserCreationForm(UserCreationForm):
    submission_token = forms.CharField(widget=forms.HiddenInput, required=False)
    current_address = forms.CharField(max_length=255, required=False, label="Current Address")
    permanent_address = forms.CharField(max_length=255, required=False, label="Permanent Address")
    country = forms.CharField(max_length=100, required=False, label="Country")
    state = forms.CharField(max_length=100, required=False, label="State/Region")
    city = forms.CharField(max_length=100, required=False, label="City")
    postal_code = forms.CharField(max_length=20, required=False, label="Postal Code")
    address_type = forms.CharField(max_length=50, required=False, label="Address Type")
    emergency_contact = forms.CharField(max_length=100, required=False, label="Emergency Contact")
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False, label="Groups")
    user_permissions = forms.ModelMultipleChoiceField(queryset=Permission.objects.all(), required=False, label="User Permissions")

    class Meta:
        model = User
        fields = (
            'username', 'email', 'password1', 'password2', 'first_name', 'last_name',
            'phone_number', 'job_title', 'avatar', 'department', 'role', 'approval_limit',
            'manager', 'hire_date', 'termination_date', 'employment_status', 'employee_type',
            'salary', 'groups', 'user_permissions', 'current_address', 'permanent_address',
            'country', 'state', 'city', 'postal_code', 'address_type', 'emergency_contact'
        )

    def clean_submission_token(self):
        return self.cleaned_data.get('submission_token') or str(uuid.uuid4())

    def clean_postal_code(self):
        postal_code = self.cleaned_data.get('postal_code')
        if postal_code and not postal_code.strip():
            logger.debug("Cleaning postal_code: setting empty string to None")
            return None
        return postal_code

    def clean_termination_date(self):
        termination_date = self.cleaned_data.get('termination_date')
        if termination_date and termination_date > timezone.now().date():
            logger.error("Invalid termination date: Future date provided")
            raise forms.ValidationError('Termination date cannot be in the future.')
        if termination_date and self.cleaned_data.get('hire_date') and termination_date < self.cleaned_data.get('hire_date'):
            logger.error("Invalid termination date: Before hire date")
            raise forms.ValidationError('Termination date cannot be before hire date.')
        return termination_date

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number or not phone_number.strip():
            logger.debug(f"Cleaning phone_number for {self.cleaned_data.get('username', 'unknown')}: setting empty/None to None")
            return None
        try:
            parsed = phonenumbers.parse(phone_number, None)
            if not phonenumbers.is_valid_number(parsed):
                logger.error(f"Phone number validation failed for {self.cleaned_data.get('username', 'unknown')}: {phone_number}")
                raise forms.ValidationError('Phone number must be a valid international number (e.g., +1234567890).')
            normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            logger.debug(f"Normalized phone number for {self.cleaned_data.get('username', 'unknown')}: {normalized}")
            return normalized
        except phonenumbers.NumberParseException as e:
            logger.error(f"Phone number parsing failed for {self.cleaned_data.get('username', 'unknown')}: {phone_number}, error: {e}")
            raise forms.ValidationError('Phone number must be in international format (e.g., +1234567890).')

    def save(self, commit=True, user=None):
        with transaction.atomic():
            logger.info(f"Saving CustomUserCreationForm for username: {self.cleaned_data.get('username')}, user={user}")
            user_instance = super().save(commit=False)
            user_instance.email = self.cleaned_data['email']
            user_instance.first_name = self.cleaned_data.get('first_name', '')
            user_instance.last_name = self.cleaned_data.get('last_name', '')
            user_instance.phone_number = self.cleaned_data.get('phone_number')
            user_instance.job_title = self.cleaned_data.get('job_title', '')
            user_instance.avatar = self.cleaned_data.get('avatar')
            user_instance.department = self.cleaned_data.get('department', 'FIN')
            user_instance.role = self.cleaned_data.get('role', 'FIN_MANAGER')
            user_instance.approval_limit = self.cleaned_data.get('approval_limit', Decimal('0.00'))
            user_instance.manager = self.cleaned_data.get('manager')
            user_instance.hire_date = self.cleaned_data.get('hire_date')
            user_instance.termination_date = self.cleaned_data.get('termination_date')
            user_instance.employment_status = self.cleaned_data.get('employment_status', 'ACTIVE')
            user_instance.employee_type = self.cleaned_data.get('employee_type', 'FULL_TIME')
            user_instance.salary = self.cleaned_data.get('salary')

            address_data = {
                'current_address': self.cleaned_data.get('current_address', ''),
                'permanent_address': self.cleaned_data.get('permanent_address', ''),
                'country': self.cleaned_data.get('country', ''),
                'state': self.cleaned_data.get('state', ''),
                'city': self.cleaned_data.get('city', ''),
                'postal_code': self.cleaned_data.get('postal_code', ''),
                'address_type': self.cleaned_data.get('address_type', ''),
                'emergency_contact': self.cleaned_data.get('emergency_contact', ''),
            }
            logger.debug(f"Address data for new user: {address_data}")

            if commit:
                try:
                    user_instance.save(user=user)
                    logger.info(f"User created successfully: {user_instance.username}, id: {user_instance.id}")
                    if any(address_data.values()):
                        logger.info(f"Non-empty address data provided for user: {user_instance.username}")
                        address = Address.objects.create(**address_data, created_by=user, updated_by=user)
                        user_instance.address = address
                        user_instance.save(user=user)
                        logger.info(f"Address created and associated with user: {user_instance.username}, address_id: {address.id}")
                    user_instance.groups.set(self.cleaned_data.get('groups', []))
                    user_instance.user_permissions.set(self.cleaned_data.get('user_permissions', []))
                    logger.info(f"Set groups and permissions for user: {user_instance.username}")
                except ValidationError as e:
                    logger.error(f"Validation error saving user {user_instance.username}: {e}", exc_info=True)
                    raise
                except Exception as e:
                    logger.error(f"Failed to save user {user_instance.username}: {e}", exc_info=True)
                    raise
            return user_instance
