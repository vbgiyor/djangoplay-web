import json
import logging

import redis
from core.utils.redis_client import redis_client
from django.contrib.auth import get_user_model
from policyengine import PERMISSION_DEPARTMENTS, PERMISSION_ROLES, get_user_role, is_user_active
from rest_framework import permissions

logger = logging.getLogger('locations.permissions')

User = get_user_model()

class LocationPermission(permissions.BasePermission):

    """Permission class for Location-related models with role and department-based access."""

    READ_ROLES = PERMISSION_ROLES.get('read', [])
    WRITE_ROLES = {'CEO', 'DJGO', 'CFO'}  # Restricted to CEO, DJGO, CFO
    DELETE_ROLES = {'CEO', 'DJGO', 'CFO'}  # Restricted to CEO, DJGO, CFO
    ALLOWED_READ_DEPARTMENTS = PERMISSION_DEPARTMENTS.get('read', [])
    ALLOWED_WRITE_DEPARTMENTS = PERMISSION_DEPARTMENTS.get('write', [])
    CUSTOM_READ_ACTIONS = {'list', 'retrieve', 'search', 'autocomplete'}

    def _get_user_role_and_department(self, request):
        """Retrieve user role and department with caching."""
        if not request.user.is_authenticated:
            return None, None
        cache_key = f"user_roles:{request.user.id}"
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for user roles: {str(e)}")

        role = get_user_role(request.user)
        department = getattr(request.user, 'department', None)
        department_code = department.code if department else None
        try:
            redis_client.setex(cache_key, 3600, json.dumps((role, department_code)))
        except redis.RedisError as e:
            logger.warning(f"Failed to cache user roles: {str(e)}")
        return role, department_code

    def has_permission(self, request, view):
        """Check view-level permissions for Location-related actions."""
        logger.debug(f"Checking view-level permission for action: {view.action}, user: {request.user}")
        if not request.user.is_authenticated:
            logger.warning("Permission denied: Unauthenticated user")
            return False
        if request.user.is_superuser:
            logger.debug(f"Permission granted: Superuser access for user: {request.user}")
            return True
        if not is_user_active(request.user):
            logger.warning(f"Permission denied: Inactive user {request.user}")
            return False

        user_role, user_department = self._get_user_role_and_department(request)
        if not user_role or not user_department:
            logger.warning(f"Permission denied: No role/department for user: {request.user}")
            return False

        is_read_action = view.action in self.CUSTOM_READ_ACTIONS or request.method in permissions.SAFE_METHODS
        is_write_action = view.action in ['create', 'update', 'partial_update']
        is_delete_action = view.action in ['destroy', 'soft_delete']

        if is_read_action and user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
            logger.debug(f"Read permission granted for {view.action or request.method} to user: {request.user}")
            return True
        if is_write_action and user_role in self.WRITE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS:
            logger.debug(f"Write permission granted for {view.action} to user: {request.user}")
            return True
        if is_delete_action and user_role in self.DELETE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS:
            logger.debug(f"Delete permission granted for {view.action} to user: {request.user}")
            return True

        logger.warning(f"Permission denied for {view.action or request.method} to user: {request.user}")
        return False

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for Location-related instances."""
        logger.debug(f"Checking object permission for {view.action or request.method} on {obj.__class__.__name__}: {obj}")
        if not request.user.is_authenticated:
            logger.warning("Object permission denied: Unauthenticated user")
            return False
        if request.user.is_superuser:
            logger.debug(f"Object permission granted: Superuser access for user: {request.user}")
            return True
        if not is_user_active(request.user):
            logger.warning(f"Object permission denied: Inactive user {request.user}")
            return False

        user_role, user_department = self._get_user_role_and_department(request)
        if not user_role or not user_department:
            logger.warning(f"Object permission denied: No role/department for user: {request.user}")
            return False

        is_read_action = view.action in self.CUSTOM_READ_ACTIONS or request.method in permissions.SAFE_METHODS
        is_write_action = view.action in ['update', 'partial_update']
        is_delete_action = view.action in ['destroy', 'soft_delete']

        if is_read_action and user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
            logger.debug(f"Read object permission granted for {view.action or request.method} to user: {request.user}")
            return True
        if is_write_action and user_role in self.WRITE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS:
            logger.debug(f"Write object permission granted for {view.action} to user: {request.user}")
            return True
        if is_delete_action and user_role in self.DELETE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS:
            logger.debug(f"Delete object permission granted for {view.action} to user: {request.user}")
            return True

        logger.warning(f"Object permission denied for {view.action or request.method} to user: {request.user}")
        return False

# import logging
# from rest_framework import permissions
# from django.contrib.auth import get_user_model

# User = get_user_model()
# logger = logging.getLogger('locations.permissions')

# class LocationPermission(permissions.BasePermission):
#     """
#     Custom permission for location-related views.
#     Allows read-only access for authenticated users, write access for specific roles,
#     and soft delete/restore for authorized roles or object creators.
#     """
#     def has_permission(self, request, view):
#         """
#         Check view-level permissions for the requested action.
#         """
#         logger.debug(f"Checking has_permission for user {request.user} on view {view}")
#         # Allow read-only access to authenticated users
#         if request.method in permissions.SAFE_METHODS:
#             logger.info(f"Read-only access granted for user {request.user}")
#             return request.user.is_authenticated

#         # Allow create/update/delete/restore for specific roles
#         allowed_roles = ['CEO', 'CFO', 'FIN_MANAGER', 'TAX_DIRECTOR', 'TAX_ANALYST']
#         has_permission = request.user.is_authenticated and (
#             request.user.is_superuser or
#             request.user.role in allowed_roles
#         )
#         logger.info(f"Write access {'granted' if has_permission else 'denied'} for user {request.user}")
#         return has_permission

#     def has_object_permission(self, request, view, obj):
#         """
#         Check object-level permissions for specific actions.
#         """
#         logger.debug(f"Checking has_object_permission for user {request.user} on object {obj}")
#         # Read permissions for all authenticated users
#         if request.method in permissions.SAFE_METHODS:
#             logger.info(f"Object read access granted for user {request.user} on {obj}")
#             return request.user.is_authenticated

#         # Write, soft delete, and restore permissions for superusers, specific roles, or object creators
#         allowed_roles = ['CEO', 'CFO', 'FIN_MANAGER']
#         has_permission = (
#             request.user.is_superuser or
#             request.user.role in allowed_roles or
#             (hasattr(obj, 'created_by') and obj.created_by == request.user)
#         )
#         logger.info(f"Object write access {'granted' if has_permission else 'denied'} for user {request.user} on {obj}")
#         return has_permission
