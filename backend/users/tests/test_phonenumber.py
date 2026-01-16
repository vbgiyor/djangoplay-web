from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from users.models.employee import User
from users.tests.forms import CustomUserChangeForm


class UserFormTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            department='FIN',
            role='DJANGO',
            approval_limit=Decimal('99999999.99'),
            employment_status='ACTIVE',
            employee_type='FULL_TIME'
        )
        self.client.login(username='admin', password='testpass123')
        self.user = User.objects.create_user(
            username='moore.jackson',
            email='jackson@example.com',
            phone_number='+447812345678',
            department='FIN',
            role='FIN_MANAGER',
            approval_limit=Decimal('1000.00'),
            employment_status='ACTIVE',
            employee_type='FULL_TIME',
            created_by=self.superuser
        )

    def test_unchanged_phone_number(self):
        form_data = {
            'username': self.user.username,
            'email': self.user.email,
            'phone_number': self.user.phone_number,
            'department': self.user.department,
            'role': self.user.role,
            'approval_limit': str(self.user.approval_limit),
            'employment_status': self.user.employment_status,
            'employee_type': self.user.employee_type,
        }
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertEqual(form.instance.created_by, self.superuser)

    def test_valid_japanese_phone_number(self):
        form_data = {
            'username': self.user.username,
            'email': self.user.email,
            'phone_number': '+819073628154',  # Japanese phone number
            'department': self.user.department,
            'role': self.user.role,
            'approval_limit': str(self.user.approval_limit),
            'employment_status': self.user.employment_status,
            'employee_type': self.user.employee_type,
        }
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertEqual(form.cleaned_data['phone_number'], '+819073628154')
        self.assertEqual(form.instance.created_by, self.superuser)

    def test_unchanged_phone_number_admin_save(self):
        url = reverse('admin:users_user_change', args=[self.user.pk])
        form_data = {
            'username': self.user.username,
            'email': self.user.email,
            'phone_number': self.user.phone_number,
            'department': self.user.department,
            'role': self.user.role,
            'approval_limit': str(self.user.approval_limit),
            'employment_status': self.user.employment_status,
            'employee_type': self.user.employee_type,
            '_save': 'Save'
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, 302, msg=f"Admin save failed: {response.content}")
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, '+447812345678')
        self.assertEqual(self.user.created_by, self.superuser)
        self.assertIsInstance(self.user.created_by, User, msg="created_by is not a User object")

    def test_japanese_phone_number_admin_save(self):
        url = reverse('admin:users_user_change', args=[self.user.pk])
        form_data = {
            'username': self.user.username,
            'email': self.user.email,
            'phone_number': '+819073628154',  # Japanese phone number
            'department': self.user.department,
            'role': self.user.role,
            'approval_limit': str(self.user.approval_limit),
            'employment_status': self.user.employment_status,
            'employee_type': self.user.employee_type,
            '_save': 'Save'
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, 302, msg=f"Admin save failed: {response.content}")
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, '+819073628154')
        self.assertEqual(self.user.created_by, self.superuser)
        self.assertIsInstance(self.user.created_by, User, msg="created_by is not a User object")
