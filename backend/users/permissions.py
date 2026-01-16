import logging

from core.permissions import BaseAppPermission
from policyengine import PERMISSION_DEPARTMENTS, PERMISSION_ROLES
from rest_framework import permissions

logger = logging.getLogger('users.permissions')

class EmployeePermission(BaseAppPermission):

    """Permission class for Employee-related models with role/department-based access."""

    READ_ROLES = PERMISSION_ROLES['read']
    WRITE_ROLES = PERMISSION_ROLES['write']
    DELETE_ROLES = PERMISSION_ROLES['delete']
    ALLOWED_READ_DEPARTMENTS = PERMISSION_DEPARTMENTS['read']
    ALLOWED_WRITE_DEPARTMENTS = PERMISSION_DEPARTMENTS['write']
    CUSTOM_READ_ACTIONS = {'list', 'retrieve', 'search', 'autocomplete'}

    def has_permission(self, request, view):
        """Check view-level permissions for EmployeeViewSet actions."""
        if view.action in self.CUSTOM_READ_ACTIONS:
            validation_result = self._validate_user(request)
            if validation_result is False:
                logger.warning(f"Permission denied for {view.action} to user: {request.user}")
                return False
            if validation_result is True:  # Superuser
                logger.debug(f"Superuser {request.user} granted access for {view.action}")
                return True
            user_role, user_department = validation_result
            if user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
                logger.debug(f"Permission granted for {view.action} to user: {request.user}, role: {user_role}, department: {user_department}")
                return True
            logger.warning(f"Permission denied for {view.action} to user: {request.user}, role: {user_role}, department: {user_department}")
            return False
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for Employee instances."""
        if not hasattr(obj, 'employee_code'):  # Ensure it's an Employee instance
            logger.warning(f"Object {obj} is not an Employee instance for user {request.user}")
            return False

        if view.action in self.CUSTOM_READ_ACTIONS or request.method in permissions.SAFE_METHODS:
            validation_result = self._validate_user(request)
            if validation_result is False:
                logger.warning(f"Read object permission denied for {view.action or request.method} to user: {request.user} on object: {obj}")
                return False
            if validation_result is True:  # Superuser
                logger.debug(f"Superuser {request.user} granted read access to object: {obj}")
                return True
            user_role, user_department = validation_result
            if user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
                logger.debug(f"Read object permission granted for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
                return True
            logger.warning(f"Read object permission denied for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
            return False

        # Handle write/delete actions
        validation_result = self._validate_user(request)
        if validation_result is False:
            logger.warning(f"Write/delete permission denied for {view.action or request.method} to user: {request.user} on object: {obj}")
            return False
        if validation_result is True:  # Superuser
            logger.debug(f"Superuser {request.user} granted write/delete access to object: {obj}")
            return True
        user_role, user_department = validation_result
        if (request.method in ['PUT', 'PATCH'] and
                user_role in self.WRITE_ROLES and
                user_department in self.ALLOWED_WRITE_DEPARTMENTS):
            logger.debug(f"Write permission granted for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
            return True
        if (request.method == 'DELETE' and
                user_role in self.DELETE_ROLES and
                user_department in self.ALLOWED_WRITE_DEPARTMENTS):
            logger.debug(f"Delete permission granted for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
            return True
        logger.warning(f"Write/delete permission denied for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
        return False


class MemberPermission(BaseAppPermission):

    """Permission class for Member-related models with strict read-only access for verified/active members."""

    READ_ROLES = PERMISSION_ROLES['read']
    ALLOWED_READ_DEPARTMENTS = PERMISSION_DEPARTMENTS['read']
    CUSTOM_READ_ACTIONS = {'list', 'retrieve', 'search', 'autocomplete'}

    def has_permission(self, request, view):
        """Check view-level permissions for MemberViewSet actions."""
        logger.debug(f"Checking view permission for action: {view.action}, user: {request.user}")
        if view.action in self.CUSTOM_READ_ACTIONS:
            validation_result = self._validate_user(request)
            if validation_result is False:
                logger.warning(f"Permission denied for {view.action} to user: {request.user}")
                return False
            if validation_result is True:  # Superuser
                logger.debug(f"Superuser {request.user} granted access for {view.action}")
                return True
            user_role, user_department = validation_result
            # Additional check for members: must be verified and have active status via member_profile
            member_profile = getattr(request.user, 'member_profile', None)
            if not member_profile or not request.user.is_verified or member_profile.status.code != 'ACTV':
                logger.warning(f"Permission denied: Unverified or inactive member: {request.user}")
                return False
            if user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
                logger.debug(f"Read permission granted for {view.action} to member: {request.user}, role: {user_role}, department: {user_department}")
                return True
            logger.warning(f"Permission denied for {view.action} to user: {request.user}, role: {user_role}, department: {user_department}")
            return False
        # Deny write/delete for members
        logger.warning(f"Permission denied: Write/delete actions not allowed for member: {request.user}")
        return False

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for Member instances (read-only)."""
        if not hasattr(obj, 'member_code'):  # Ensure it's a Member instance
            logger.warning(f"Object {obj} is not a Member instance for user {request.user}")
            return False

        # Members are read-only
        if view.action in self.CUSTOM_READ_ACTIONS or request.method in permissions.SAFE_METHODS:
            return self.has_permission(request, view)
        # Deny write/delete
        logger.warning(f"Object permission denied: Write/delete not allowed for member: {request.user} on object: {obj}")
        return False
