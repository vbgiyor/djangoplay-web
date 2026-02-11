import logging

from core.permissions import BaseAppPermission
from entities.models.entity import Entity
from fincore.exceptions import FincoreValidationError
from fincore.models.address import Address
from fincore.models.contact import Contact
from fincore.models.tax_profile import TaxProfile
from policyengine import PERMISSION_DEPARTMENTS, PERMISSION_ROLES
from rest_framework import permissions
from teamcentral.models import MemberProfile

logger = logging.getLogger(__name__)

class FincorePermission(BaseAppPermission):

    """Permission class for fincore models (Address, Contact, TaxProfile), controlling access based on roles, departments, and entity ownership via FincoreEntityMapping."""

    READ_ROLES = PERMISSION_ROLES['read']
    WRITE_ROLES = PERMISSION_ROLES['write']
    DELETE_ROLES = PERMISSION_ROLES['delete']
    ALLOWED_READ_DEPARTMENTS = PERMISSION_DEPARTMENTS['read']
    ALLOWED_WRITE_DEPARTMENTS = PERMISSION_DEPARTMENTS['write']
    CUSTOM_READ_ACTIONS = {'search_addresses', 'search_contacts', 'search_tax_profiles', 'retrieve'}

    def _get_entity(self, obj):
        """Extract the entity from the object (Address, Contact, or TaxProfile) via FincoreEntityMapping."""
        if isinstance(obj, (Address, Contact, TaxProfile)):
            if obj.entity_mapping:
                return Entity.objects.filter(
                    id=obj.entity_mapping.entity_id,
                    deleted_at__isnull=True
                ).first()
            logger.warning(f"No entity_mapping associated with object {obj}")
            return None
        logger.warning(f"Object {obj} is not an instance of Address, Contact, or TaxProfile")
        return None

    def has_permission(self, request, view):
        """Check view-level permissions for fincore ViewSet actions."""
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
        """Check object-level permissions for fincore model instances."""
        if not isinstance(obj, (Address, Contact, TaxProfile)):
            logger.warning(f"Object {obj} is not an instance of Address, Contact, or TaxProfile for user {request.user}")
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
                # Check entity ownership via Member model
                entity = self._get_entity(obj)
                if not entity:
                    logger.warning(f"No entity associated with object {obj} for user {request.user}")
                    return False
                has_entity_access = Member.objects.filter(
                    employee=request.user,
                    entity=entity,
                    status__code='ACTV',
                    entity__deleted_at__isnull=True
                ).exists()
                if has_entity_access:
                    logger.debug(f"Read object permission granted for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
                    return True
                logger.warning(f"Read object permission denied for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj} due to lack of entity access")
                return False
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
        if (request.method in ['PUT', 'PATCH', 'DELETE'] and
                user_role in self.WRITE_ROLES and
                user_department in self.ALLOWED_WRITE_DEPARTMENTS):
            # Check entity ownership via Member model
            entity = self._get_entity(obj)
            if not entity:
                logger.error(f"Cannot perform write/delete on object {obj} with no entity for user {request.user}")
                raise FincoreValidationError("Object must be associated with an entity.", code="missing_entity")
            has_entity_access = MemberProfile.objects.filter(
                employee=request.user,
                entity=entity,
                status__code='ACTV',
                entity__deleted_at__isnull=True
            ).exists()
            if has_entity_access:
                logger.debug(f"Write/delete permission granted for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
                return True
            logger.warning(f"Write/delete permission denied for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj} due to lack of entity access")
            return False
        logger.warning(f"Write/delete permission denied for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
        return False
