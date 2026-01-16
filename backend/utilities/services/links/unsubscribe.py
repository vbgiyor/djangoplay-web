# utilities/services/links/unsubscribe.py

from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from utilities.admin.url_utils import get_site_base_url


def build_unsubscribe_url(user) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("frontend:unsubscribe", kwargs={"uidb64": uid, "token": token})
    return f"{get_site_base_url()}{path}"
