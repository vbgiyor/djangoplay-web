from allauth.account.models import EmailAddress
from allauth.account.utils import user_pk_to_url_str
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.urls import reverse
from frontend.forms.password_reset import CustomResetPasswordKeyForm
from paystream.app_settings.core import SITE_URL


class Command(BaseCommand):
    help = """
    Manages password reset operations for a user by email address.

    This command retrieves a user by their email, verifies their email address record,
    generates a password reset token, and creates a password reset link. Optionally,
    it can reset the user's password to a specified value or a default password if not
    provided. Use the --link option to generate and display the reset link without
    performing the password reset.

    Example usage:
        ./manage.py resetpassword --email user@example.com
        ./manage.py resetpassword --email user@example.com --password NewPass123!
        ./manage.py resetpassword --email user@example.com --link
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='The email address of the user to perform password reset operations for.'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='djangoplay',
            help='The new password to set for the user. Defaults to "djangoplay".'
        )
        parser.add_argument(
            '--link',
            action='store_true',
            help='Generate and display the password reset link without resetting the password.'
        )

    def handle(self, *args, **options):
        email = options['email']
        new_password = options['password']
        link_only = options['link']

        # 1. Get user by email
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f"Found user: pk={user.pk}, username={user.username}, email={user.email}")
        except User.DoesNotExist:
            self.stdout.write(f"No user found with email {email}")
            return

        # 2. Verify EmailAddress record
        try:
            email_address = EmailAddress.objects.get(user=user, email=email)
            self.stdout.write(f"EmailAddress: email={email_address.email}, verified={email_address.verified}, primary={email_address.primary}")
        except EmailAddress.DoesNotExist:
            self.stdout.write(f"No EmailAddress found for {email}")

        # 3. Generate password reset token
        uidb36 = user_pk_to_url_str(user)
        token = default_token_generator.make_token(user)
        is_valid = default_token_generator.check_token(user, token)
        self.stdout.write(f"Generated token: {token}, valid: {is_valid}")

        # 4. Build and print password reset link
        try:
            factory = RequestFactory()
            request = factory.get('/accounts/password/reset/key/')
            request.META['HTTP_HOST'] = SITE_URL.replace('http://', '').replace('https://', '').rstrip('/')
            reset_path = reverse(
                "account_reset_password_from_key",
                kwargs={"uidb36": uidb36, "key": token},
            )
            # If reverse produces a hyphen, manually correct to slash
            if f"{uidb36}-{token}" in reset_path:
                reset_path = f"/accounts/password/reset/key/{uidb36}/{token}/"
            reset_link = request.build_absolute_uri(reset_path)
            self.stdout.write(f"Raw reset path: {reset_path}")
            self.stdout.write(f"Password reset link: {reset_link}")
        except Exception as e:
            self.stdout.write(f"Error generating reset link: {str(e)}")
            return

        # 5. Perform password reset if not link-only
        if not link_only:
            form = CustomResetPasswordKeyForm(data={'password1': new_password, 'password2': new_password}, user=user, temp_key=token)
            if form.is_valid():
                form.save()
                self.stdout.write("Password reset successful")
                user.refresh_from_db()
                self.stdout.write(f"New password hash: {user.password}")
                self.stdout.write(f"Password check for '{new_password}': {user.check_password(new_password)}")
            else:
                self.stdout.write(f"Form errors: {form.errors}")
