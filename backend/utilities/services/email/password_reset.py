# # utilities/services/email/password_reset.py
from celery import shared_task


@shared_task(bind=True)
def send_password_reset_email_task(
    self,
    user_id: int,
    token: str,
):
    from django.contrib.auth import get_user_model
    from users.adapters.email.engine import EmailEngine
    from utilities.admin.url_utils import get_site_base_url
    from utilities.constants.template_registry import TemplateRegistry as T

    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    reset_url = (
        f"{get_site_base_url()}/accounts/password/reset/{token}/"
    )

    EmailEngine.send(
        prefix=T.PASSWORD_RESET_EMAIL,
        email=user.email,
        context={
            "user": user,
            "reset_url": reset_url,
        },
    )
