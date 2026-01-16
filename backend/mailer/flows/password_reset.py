# # utilities/services/email/password_reset.py
from celery import shared_task

@shared_task(bind=True)
def send_password_reset_email_task(
    self,
    user_id: int,
    token: str,
):
    from django.contrib.auth import get_user_model
    from utilities.admin.url_utils import get_site_base_url
    from users.adapters.email.engine import EmailEngine
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

# from celery import shared_task
# from django.contrib.auth import get_user_model
# from allauth.account.forms import ResetPasswordForm

# User = get_user_model()

# @shared_task(bind=True, max_retries=3, default_retry_delay=30)
# def send_password_reset_email_task(self, user_id: int):
#     try:
#         user = User.objects.get(pk=user_id)
#     except User.DoesNotExist:
#         return

#     form = ResetPasswordForm(data={"email": user.email})
#     if form.is_valid():
#         # ⚠️ This will call adapter.send_mail()
#         form.save(request=None)


# import logging
# from celery import shared_task
# from django.contrib.auth import get_user_model
# from allauth.account.adapter import get_adapter

# logger = logging.getLogger(__name__)
# UserModel = get_user_model()


# @shared_task(
#     bind=True,
#     max_retries=2,
#     default_retry_delay=60,
#     name="utilities.services.password_reset.send_password_reset_email_task",
# )
# def send_password_reset_email_task(self, user_id: int) -> bool:
#     """
#     Celery wrapper for allauth password-reset email.
#     """
#     try:
#         user = UserModel.objects.get(pk=user_id, is_active=True)
#     except UserModel.DoesNotExist:
#         logger.warning(
#             "send_password_reset_email_task: user_id=%s not found",
#             user_id,
#         )
#         return False

#     adapter = get_adapter()
#     adapter.request = None  # Celery-safe    
#     try:
#         result = adapter.send_mail(
#             "password_reset",
#             user.email,
#             {"user": user},            
#         )
#         logger.info(
#             "send_password_reset_email_task: email sent → %s",
#             user.email,
#         )
#         return bool(result)
#     except Exception:
#         logger.exception(
#             "send_password_reset_email_task: failed for user_id=%s",
#             user.pk,
#         )
#         return False
