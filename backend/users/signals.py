import logging

from django.apps import apps
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from users.exceptions import MemberValidationError

# ⛔️ REMOVED:
# from policyengine.components.ssopolicies import setup_role_based_group
# from users.constants import ROLE_CODES

logger = logging.getLogger(__name__)


@receiver(post_save, sender='users.Member')
def assign_member_viewer_group(sender, instance, created, **kwargs):
    """Assign Viewer group to SSO members after Member creation or update."""
    from policyengine.components.ssopolicies import setup_role_based_group  # ← lazy import

    employee = instance.employee
    is_sso_user = (
        employee.is_verified
        and (employee.role.code == 'SSO' or employee.employee_type.code == 'SSO')
    )
    if is_sso_user:
        try:
            sso_group = setup_role_based_group("SSO")
            employee.groups.add(sso_group)
            logger.info(f"Assigned Viewer group to SSO member: {instance.member_code}")
        except Exception as e:
            logger.error(
                f"Failed to assign Viewer group to member {instance.member_code}: {str(e)}"
            )
            raise MemberValidationError(
                "Failed to assign Viewer group.",
                code="invalid_permissions",
                details={"error": str(e)},
            )


@receiver(post_save, sender='users.Employee')
def assign_employee_viewer_group(sender, instance, created, **kwargs):
    """Assign Viewer group to employees with any role after Employee creation or update."""
    from policyengine.components.ssopolicies import setup_role_based_group  # ← lazy import

    from users.constants import ROLE_CODES  # ← lazy import

    employee = instance
    if employee.is_verified and employee.role and employee.role.code in ROLE_CODES.keys():
        try:
            sso_group = setup_role_based_group("SSO")
            employee.groups.add(sso_group)
            logger.info(f"Assigned Viewer group to employee: {employee.employee_code}")
        except Exception as e:
            logger.error(
                f"Failed to assign Viewer group to employee {employee.employee_code}: {str(e)}"
            )
            raise MemberValidationError(
                "Failed to assign Viewer group.",
                code="invalid_permissions",
                details={"error": str(e)},
            )


@receiver(post_save, sender='users.SignUpRequest')
def handle_sso_signup(sender, instance, created, **kwargs):
    """Handle signup request, restore deleted Member account if exists or create new."""
    Member = apps.get_model('users', 'Member')
    apps.get_model('users', 'Employee')
    if created:
        try:
            query = Q(email__iexact=instance.user.email, deleted_at__isnull=False)
            if instance.sso_provider != 'EMAIL' and instance.sso_id:
                query |= Q(employee__sso_id=instance.sso_id, deleted_at__isnull=False)

            deleted_member = Member.objects.filter(query).first()
            if deleted_member:
                deleted_member.deleted_at = None
                deleted_member.deleted_by = None
                deleted_member.email = instance.user.email

                if instance.user.is_verified:
                    active_status = apps.get_model('users', 'MemberStatus').objects.get(
                        code='ACTV'
                    )
                    deleted_member.status = active_status

                deleted_member.save()
                logger.info(f"Restored deleted member account: {deleted_member.member_code}")

                from teamcentral.services import MemberLifecycleService
                MemberLifecycleService.send_welcome_back_email(deleted_member)
            else:
                if not Member.objects.filter(
                    employee=instance.user, deleted_at__isnull=True
                ).exists():
                    from teamcentral.services import MemberLifecycleService
                    member_data = {
                        'email': instance.user.email,
                        'first_name': instance.user.first_name,
                        'last_name': instance.user.last_name,
                        'employee': instance.user,
                        'status': apps.get_model('users', 'MemberStatus').objects.get(
                            code='ACTV' if instance.user.is_verified else 'PEND'
                        ),
                    }
                    MemberLifecycleService.create_member(member_data, created_by=instance.user)
                    logger.info(
                        f"Created new member for SignUpRequest: {instance.user.email}"
                    )
        except Exception as e:
            logger.error(f"Failed to handle signup for {instance.user.email}: {str(e)}")
            raise MemberValidationError(
                "Failed to process signup.",
                code="member_restore_error",
                details={"error": str(e)},
            )


@receiver(user_logged_in)
def log_user_sign_in(sender, user, request, **kwargs):
    """Log user sign-in activity."""
    try:
        client_ip = request.META.get('REMOTE_ADDR') or request.META.get(
            'HTTP_X_FORWARDED_FOR'
        )
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        logger.info(f"Logged SIGN_IN for user: {user}")
    except Exception as e:
        logger.error(f"Failed to log SIGN_IN for user {user}: {str(e)}")


@receiver(user_logged_out)
def log_user_sign_out(sender, user, request, **kwargs):
    if not request:
        logger.debug("Skipping SIGN_OUT log: request is None")
        return

    try:
        if user:
            client_ip = request.META.get('REMOTE_ADDR') or request.META.get(
                'HTTP_X_FORWARDED_FOR'
            )
            if client_ip and ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()
            logger.info(f"Logged SIGN_OUT for user: {user}")
        else:
            logger.debug("Skipping SIGN_OUT log: user is None")
    except Exception as e:
        logger.error(f"Failed to log SIGN_OUT for user {user}: {str(e)}")


@receiver(post_save, sender='users.Employee')
def log_user_sign_up(sender, instance, created, **kwargs):
    """Log user sign-up activity."""
    if created:
        try:
            logger.info(f"Logged SIGN_UP for user: {instance}")
        except Exception as e:
            logger.error(f"Failed to log SIGN_UP for user {instance}: {str(e)}")

