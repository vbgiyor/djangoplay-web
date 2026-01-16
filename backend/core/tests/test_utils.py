from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django_countries.fields import Country

from core.utils import get_current_client_ip, get_machine_ip, thread_local, validate_postal_code, validate_state_country_match


class MockState:
    def __init__(self, country):
        self.country = country

class UtilsTest(TestCase):
    def tearDown(self):
        """Clear thread_local after each test to prevent state leakage."""
        thread_local.client_ip = None

    def test_get_machine_ip(self):
        """Test get_machine_ip retrieves a valid IP or returns None on failure."""
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.getsockname.return_value = ('192.168.1.1', 0)
            ip = get_machine_ip()
            self.assertEqual(ip, '192.168.1.1')
            mock_socket.return_value.connect.assert_called_once_with(('8.8.8.8', 80))
            mock_socket.return_value.close.assert_called_once()

        with patch('socket.socket') as mock_socket:
            mock_socket.side_effect = Exception('Connection failed')
            ip = get_machine_ip()
            self.assertIsNone(ip)

    def test_get_current_client_ip(self):
        """Test get_current_client_ip retrieves IP from thread_local or returns default."""
        # Test when IP is set
        thread_local.client_ip = '127.0.0.1'
        self.assertEqual(get_current_client_ip(), '127.0.0.1')

        # Test default when IP is not set
        thread_local.client_ip = None
        self.assertEqual(get_current_client_ip(default='N/A'), 'N/A')

    def test_validate_postal_code_valid(self):
        """Test validate_postal_code with valid postal codes."""
        test_cases = [
            ('12345', 'US'),
            ('12345-6789', 'US'),
            ('123456', 'IN'),
            ('A1A 1A1', 'CA'),
            ('SW1A 1AA', 'GB'),
            ('123456', 'SG'),
            ('123-4567', 'JP'),
            ('1234', 'AU'),
            ('1234', 'LU'),
            ('1234', 'CH'),
            ('12345', 'DE'),
            ('1234567', 'CL'),
            ('12345', 'UY'),
            ('', 'PA'),
            ('', 'QA'),
            ('', 'AE'),
            ('12345', 'SA'),
            ('12345', 'MV'),
            ('1234', 'ZA'),
            ('123456', 'NG'),
            ('12345', 'KE'),
            ('12345', 'MX'),
        ]
        for postal_code, country_code in test_cases:
            with self.subTest(postal_code=postal_code, country_code=country_code):
                try:
                    validate_postal_code(postal_code, country_code)
                except ValidationError:
                    self.fail(f"Valid postal code {postal_code} for {country_code} raised ValidationError")

    def test_validate_postal_code_invalid(self):
        """Test validate_postal_code with invalid postal codes."""
        test_cases = [
            ('1234', 'US'),     # Too short
            ('123456', 'US'),   # Too long
            ('12-345', 'US'),   # Wrong format
            ('12345A', 'IN'),   # Letters not allowed
            ('A1A1A', 'CA'),    # Wrong format (replaced A1A1A1)
            ('SW1A 1A', 'GB'),  # Wrong format
            ('12345', 'SG'),    # Too short
            ('123456', 'JP'),   # Missing hyphen
            ('123', 'AU'),      # Too short
            ('12345', 'LU'),    # Too long
            ('12A3', 'CH'),     # Letters not allowed
            ('1234A', 'DE'),    # Letters not allowed
            ('123456', 'CL'),   # Too short
            ('1234', 'UY'),     # Too short
            ('123', 'PA'),      # Should be empty
            ('123', 'QA'),      # Should be empty
            ('123', 'AE'),      # Should be empty
            ('1234', 'SA'),     # Too short
            ('1234', 'MV'),     # Too short
            ('123', 'ZA'),      # Too short
            ('12345', 'NG'),    # Too short
            ('1234', 'KE'),     # Too short
            ('1234', 'MX'),     # Too short
        ]
        for postal_code, country_code in test_cases:
            with self.subTest(postal_code=postal_code, country_code=country_code):
                with self.assertRaises(ValidationError, msg=f"Postal code {postal_code} for {country_code} should be invalid"):
                    validate_postal_code(postal_code, country_code)

    def test_validate_state_country_match_valid(self):
        """Test validate_state_country_match with matching state and country."""
        country = Country('US')
        state = MockState(country=country)
        try:
            validate_state_country_match(state, country)
        except ValidationError:
            self.fail("Valid state-country match raised ValidationError")

    def test_validate_state_country_match_invalid(self):
        """Test validate_state_country_match with mismatched state and country."""
        country_us = Country('US')
        country_ca = Country('CA')
        state = MockState(country=country_us)
        with self.assertRaises(ValidationError):
            validate_state_country_match(state, country_ca)

    def test_validate_state_country_match_null_values(self):
        """Test validate_state_country_match with None values."""
        validate_state_country_match(None, Country('US'))  # Should not raise
        validate_state_country_match(MockState(Country('US')), None)  # Should not raise
        validate_state_country_match(None, None)  # Should not raise
