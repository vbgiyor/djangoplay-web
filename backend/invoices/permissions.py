import json
import logging

import redis
from core.utils.redis_client import redis_client
from policyengine import PERMISSION_DEPARTMENTS, PERMISSION_ROLES
from rest_framework import permissions

logger = logging.getLogger('invoices.permissions')

class InvoicePermission(permissions.BasePermission):

    """Permission class for Invoice-related models with role, department, and entity-based access."""

    READ_ROLES = PERMISSION_ROLES.get('read', [])
    WRITE_ROLES = PERMISSION_ROLES.get('write', [])
    DELETE_ROLES = PERMISSION_ROLES.get('delete', [])
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

        role = getattr(request.user, 'role', None)
        department = getattr(request.user, 'department', None)
        try:
            redis_client.setex(cache_key, 3600, json.dumps((role, department)))
        except redis.RedisError as e:
            logger.warning(f"Failed to cache user roles: {str(e)}")
        return role, department

    def has_permission(self, request, view):
        """Check view-level permissions for Invoice-related actions."""
        logger.debug(f"Checking view-level permission for action: {view.action}, user: {request.user}")
        if not request.user.is_authenticated:
            logger.warning("Permission denied: Unauthenticated user")
            return False
        if request.user.is_superuser:
            logger.debug(f"Permission granted: Superuser access for user: {request.user}")
            return True

        user_role, user_department = self._get_user_role_and_department(request)
        if not user_role or not user_department:
            logger.warning(f"Permission denied: No role/department for user: {request.user}")
            return False

        is_read_action = view.action in self.CUSTOM_READ_ACTIONS or request.method in permissions.SAFE_METHODS
        is_write_action = view.action in ['create', 'update', 'partial_update', 'destroy', 'restore']

        if is_read_action and user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
            logger.debug(f"Read permission granted for {view.action or request.method} to user: {request.user}")
            return True
        if is_write_action and user_role in self.WRITE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS:
            logger.debug(f"Write permission granted for {view.action} to user: {request.user}")
            return True

        logger.warning(f"Permission denied for {view.action or request.method} to user: {request.user}")
        return False

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for Invoice-related instances."""
        logger.debug(f"Checking object permission for {view.action or request.method} on {obj.__class__.__name__}: {obj}")
        if not request.user.is_authenticated:
            logger.warning("Object permission denied: Unauthenticated user")
            return False
        if request.user.is_superuser:
            logger.debug(f"Object permission granted: Superuser access for user: {request.user}")
            return True

        user_role, user_department = self._get_user_role_and_department(request)
        if not user_role or not user_department:
            logger.warning(f"Object permission denied: No role/department for user: {request.user}")
            return False

        # Use service layer for accessible entities
        from invoices.services.invoice import get_accessible_entities
        accessible_entities = get_accessible_entities(request.user)

        # Determine entity fields based on model type
        entity_fields = {
            'Invoice': ['issuer', 'recipient'],
            'LineItem': ['invoice__issuer', 'invoice__recipient'],
            'Payment': ['invoice__issuer', 'invoice__recipient'],
            'BillingSchedule': ['entity'],
            'PaymentMethod': [],  # Global access
            'Status': [],  # Global access
            'GSTConfiguration': []  # Global access
        }.get(obj.__class__.__name__, [])

        has_access = not entity_fields  # Global models have no entity restriction
        for field in entity_fields:
            try:
                entity = obj
                for attr in field.split('__'):
                    entity = getattr(entity, attr)
                if entity.id in accessible_entities:
                    has_access = True
                    break
            except AttributeError:
                continue

        if not has_access:
            logger.warning(f"Object permission denied: User {request.user} not associated with entities in {obj}")
            return False

        is_read_action = view.action in self.CUSTOM_READ_ACTIONS or request.method in permissions.SAFE_METHODS
        is_write_action = view.action in ['update', 'partial_update', 'destroy', 'restore']

        if is_read_action and user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
            logger.debug(f"Read object permission granted for {view.action or request.method} to user: {request.user}")
            return True
        if is_write_action and user_role in self.WRITE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS:
            logger.debug(f"Write object permission granted for {view.action} to user: {request.user}")
            return True

        logger.warning(f"Object permission denied for {view.action or request.method} to user: {request.user}")
        return False
