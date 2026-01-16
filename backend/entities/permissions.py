import logging

from core.permissions import BaseAppPermission
from policyengine import PERMISSION_DEPARTMENTS, PERMISSION_ROLES
from rest_framework import permissions
from users.models.member import Member

from entities.models.entity import Entity

logger = logging.getLogger(__name__)

class EntityPermission(BaseAppPermission):

    """Permission class for the Entity model, controlling access based on roles, departments, and entity ownership."""

    READ_ROLES = PERMISSION_ROLES['read']
    WRITE_ROLES = PERMISSION_ROLES['write']
    DELETE_ROLES = PERMISSION_ROLES['delete']
    ALLOWED_READ_DEPARTMENTS = PERMISSION_DEPARTMENTS['read']
    ALLOWED_WRITE_DEPARTMENTS = PERMISSION_DEPARTMENTS['write']
    CUSTOM_READ_ACTIONS = {'search', 'retrieve'}

    def has_permission(self, request, view):
        """Check view-level permissions for EntityViewSet actions."""
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
        """Check object-level permissions for Entity instances."""
        if not isinstance(obj, Entity):
            logger.warning(f"Object {obj} is not an Entity instance for user {request.user}")
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
                has_entity_access = Member.objects.filter(
                    employee=request.user,
                    entity=obj,
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
            has_entity_access = Member.objects.filter(
                employee=request.user,
                entity=obj,
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

# import logging
# from rest_framework import permissions
# from core.permissions import BaseAppPermission
# from utilities.permissions_config import PERMISSION_ROLES, PERMISSION_DEPARTMENTS
# from entities.models.entity import Entity
# from django.db import models

# logger = logging.getLogger(__name__)

# class EntityPermission(BaseAppPermission):
#     """Permission class for the Entity model, controlling access based on roles, departments, and entity ownership."""
#     READ_ROLES = PERMISSION_ROLES['read']
#     WRITE_ROLES = PERMISSION_ROLES['write']
#     DELETE_ROLES = PERMISSION_ROLES['delete']
#     ALLOWED_READ_DEPARTMENTS = PERMISSION_DEPARTMENTS['read']
#     ALLOWED_WRITE_DEPARTMENTS = PERMISSION_DEPARTMENTS['write']
#     CUSTOM_READ_ACTIONS = {'search', 'retrieve'}

#     def has_permission(self, request, view):
#         """Check view-level permissions for EntityViewSet actions."""
#         if view.action in self.CUSTOM_READ_ACTIONS:
#             validation_result = self._validate_user(request)
#             if validation_result is False:
#                 logger.warning(f"Permission denied for {view.action} to user: {request.user}")
#                 return False
#             if validation_result is True:  # Superuser
#                 logger.debug(f"Superuser {request.user} granted access for {view.action}")
#                 return True
#             user_role, user_department = validation_result
#             if user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
#                 logger.debug(f"Permission granted for {view.action} to user: {request.user}, role: {user_role}, department: {user_department}")
#                 return True
#             logger.warning(f"Permission denied for {view.action} to user: {request.user}, role: {user_role}, department: {user_department}")
#             return False
#         return super().has_permission(request, view)

#     def has_object_permission(self, request, view, obj):
#         """Check object-level permissions for Entity instances."""
#         if not isinstance(obj, Entity):
#             logger.warning(f"Object {obj} is not an Entity instance for user {request.user}")
#             return False

#         if view.action in self.CUSTOM_READ_ACTIONS or request.method in permissions.SAFE_METHODS:
#             validation_result = self._validate_user(request)
#             if validation_result is False:
#                 logger.warning(f"Read object permission denied for {view.action or request.method} to user: {request.user} on object: {obj}")
#                 return False
#             if validation_result is True:  # Superuser
#                 logger.debug(f"Superuser {request.user} granted read access to object: {obj}")
#                 return True
#             user_role, user_department = validation_result
#             if user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
#                 # Check entity ownership for read access
#                 has_entity_access = Entity.objects.filter(
#                     id=obj.id,
#                     deleted_at__isnull=True
#                 ).filter(
#                     models.Q(members__id=request.user.id) | models.Q(admins__id=request.user.id)
#                 ).exists()
#                 if has_entity_access:
#                     logger.debug(f"Read object permission granted for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
#                     return True
#                 logger.warning(f"Read object permission denied for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj} due to lack of entity access")
#                 return False
#             logger.warning(f"Read object permission denied for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
#             return False

#         # Handle write/delete actions
#         validation_result = self._validate_user(request)
#         if validation_result is False:
#             logger.warning(f"Write/delete permission denied for {view.action or request.method} to user: {request.user} on object: {obj}")
#             return False
#         if validation_result is True:  # Superuser
#             logger.debug(f"Superuser {request.user} granted write/delete access to object: {obj}")
#             return True
#         user_role, user_department = validation_result
#         if (request.method in ['PUT', 'PATCH', 'DELETE'] and
#                 user_role in self.WRITE_ROLES and
#                 user_department in self.ALLOWED_WRITE_DEPARTMENTS):
#             # Check entity ownership for write/delete
#             has_entity_access = Entity.objects.filter(
#                 id=obj.id,
#                 deleted_at__isnull=True
#             ).filter(
#                 models.Q(members__id=request.user.id) | models.Q(admins__id=request.user.id)
#             ).exists()
#             if has_entity_access:
#                 logger.debug(f"Write/delete permission granted for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
#                 return True
#             logger.warning(f"Write/delete permission denied for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj} due to lack of entity access")
#             return False
#         logger.warning(f"Write/delete permission denied for {view.action or request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
#         return False
