from .commons.base import get_user_department, get_user_role, is_user_active
from .components.actions import ACTION_PERMISSIONS
from .components.departments import PERMISSION_DEPARTMENTS
from .components.roles import PERMISSION_ROLES


def get_permissions_utils():
    from .components.permissions import ActionBasedPermission, get_action_based_permissions
    return ActionBasedPermission, get_action_based_permissions




