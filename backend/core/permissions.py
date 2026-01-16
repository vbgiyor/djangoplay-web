import logging

from policyengine import PERMISSION_DEPARTMENTS, PERMISSION_ROLES, get_user_department, get_user_role, is_user_active
from rest_framework import permissions


class BaseAppPermission(permissions.BasePermission):

    """Base permission class for role and department-based access control."""

    # Define roles and departments in subclasses
    READ_ROLES = PERMISSION_ROLES['read']
    WRITE_ROLES = PERMISSION_ROLES['write']
    DELETE_ROLES = PERMISSION_ROLES['delete']
    ALLOWED_READ_DEPARTMENTS = PERMISSION_DEPARTMENTS['read']
    ALLOWED_WRITE_DEPARTMENTS = PERMISSION_DEPARTMENTS['write']
    logger_name = 'core.permissions'

    def __init__(self):
        self.logger = logging.getLogger(self.logger_name)

    def _validate_user(self, request):
        """Validate user authentication, employment status, role, and department."""
        if not request.user or not request.user.is_authenticated:
            self.logger.warning(f"Unauthorized access attempt by user: {request.user}")
            return False
        if request.user.is_superuser:
            self.logger.debug(f"Superuser access granted for {request.method} to user: {request.user}")
            return True
        if not is_user_active(request.user):
            self.logger.warning(f"Inactive or non-employee access attempt by user: {request.user}")
            return False
        user_role = get_user_role(request.user)
        user_department = get_user_department(request.user)
        if not user_role or user_role not in self.READ_ROLES:  # Use READ_ROLES as a proxy for valid roles
            self.logger.warning(f"Invalid or missing role for user: {request.user}, role: {user_role}")
            return False
        if not user_department or user_department not in self.ALLOWED_READ_DEPARTMENTS:
            self.logger.warning(f"Invalid or missing department for user: {request.user}, department: {user_department}")
            return False
        return user_role, user_department

    def has_permission(self, request, view):
        """Check view-level permissions based on HTTP method."""
        validation_result = self._validate_user(request)
        if validation_result is False:
            return False
        if validation_result is True:  # Superuser
            return True
        user_role, user_department = validation_result

        if request.method in permissions.SAFE_METHODS:
            if user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
                self.logger.debug(f"Read permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
                return True
            self.logger.warning(f"Read permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
            return False

        if request.method == 'DELETE':
            if user_role in self.DELETE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS:
                self.logger.debug(f"Delete permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
                return True
            self.logger.warning(f"Delete permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
            return False

        if user_role in self.WRITE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS:
            self.logger.debug(f"Write permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
            return True
        self.logger.warning(f"Write permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
        return False

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions based on HTTP method."""
        validation_result = self._validate_user(request)
        if validation_result is False:
            return False
        if validation_result is True:  # Superuser
            return True
        user_role, user_department = validation_result

        if request.method in permissions.SAFE_METHODS:
            if user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
                self.logger.debug(f"Read object permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
                return True
            self.logger.warning(f"Read object permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
            return False

        if request.method == 'DELETE':
            if (user_role in self.DELETE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS) or (hasattr(obj, 'created_by') and obj.created_by == request.user):
                self.logger.debug(f"Delete object permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
                return True
            self.logger.warning(f"Delete object permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
            return False

        if (user_role in self.WRITE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS) or (hasattr(obj, 'created_by') and obj.created_by == request.user):
            self.logger.debug(f"Write object permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
            return True
        self.logger.warning(f"Write object permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
        return False

# """Base permission classes for shared use across apps."""

# import logging
# from rest_framework import permissions
# from django.contrib.auth import get_user_model
# from users.constants import ROLE_CODES, EMPLOYMENT_STATUS_CODES, DEPARTMENT_CODES

# User = get_user_model()

# # Define valid role codes from ROLE_CODES
# VALID_ROLES = {role[0] for role in ROLE_CODES}

# class BaseAppPermission(permissions.BasePermission):
#     """Base permission class for role and department-based access control."""

#     # Define roles and departments in subclasses
#     READ_ROLES = set()
#     WRITE_ROLES = set()
#     DELETE_ROLES = set()
#     ALLOWED_READ_DEPARTMENTS = set()
#     ALLOWED_WRITE_DEPARTMENTS = set()
#     logger_name = 'core.permissions'

#     def __init__(self):
#         self.logger = logging.getLogger(self.logger_name)

#     def _validate_user(self, request):
#         """Validate user authentication, employment status, role, and department."""
#         if not request.user or not request.user.is_authenticated:
#             self.logger.warning(f"Unauthorized access attempt by user: {request.user}")
#             return False
#         if request.user.is_superuser:
#             self.logger.debug(f"Superuser access granted for {request.method} to user: {request.user}")
#             return True
#         if not hasattr(request.user, 'employment_status') or request.user.employment_status != 'ACTIVE':
#             self.logger.warning(f"Inactive or non-employee access attempt by user: {request.user}")
#             return False
#         user_role = getattr(request.user, 'role', None)
#         user_department = getattr(request.user, 'department', None)
#         if not user_role or user_role not in VALID_ROLES:
#             self.logger.warning(f"Invalid or missing role for user: {request.user}, role: {user_role}")
#             return False
#         if not user_department or user_department not in {dept[0] for dept in DEPARTMENT_CODES}:
#             self.logger.warning(f"Invalid or missing department for user: {request.user}, department: {user_department}")
#             return False
#         return user_role, user_department

#     def has_permission(self, request, view):
#         """Check view-level permissions based on HTTP method."""
#         validation_result = self._validate_user(request)
#         if validation_result is False:
#             return False
#         if validation_result is True:  # Superuser
#             return True
#         user_role, user_department = validation_result

#         if request.method in permissions.SAFE_METHODS:
#             if user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
#                 self.logger.debug(f"Read permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
#                 return True
#             self.logger.warning(f"Read permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
#             return False

#         if request.method == 'DELETE':
#             if user_role in self.DELETE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS:
#                 self.logger.debug(f"Delete permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
#                 return True
#             self.logger.warning(f"Delete permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
#             return False

#         if user_role in self.WRITE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS:
#             self.logger.debug(f"Write permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
#             return True
#         self.logger.warning(f"Write permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department}")
#         return False

#     def has_object_permission(self, request, view, obj):
#         """Check object-level permissions based on HTTP method."""
#         validation_result = self._validate_user(request)
#         if validation_result is False:
#             return False
#         if validation_result is True:  # Superuser
#             return True
#         user_role, user_department = validation_result

#         if request.method in permissions.SAFE_METHODS:
#             if user_role in self.READ_ROLES and user_department in self.ALLOWED_READ_DEPARTMENTS:
#                 self.logger.debug(f"Read object permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
#                 return True
#             self.logger.warning(f"Read object permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
#             return False

#         if request.method == 'DELETE':
#             if (user_role in self.DELETE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS) or (hasattr(obj, 'created_by') and obj.created_by == request.user):
#                 self.logger.debug(f"Delete object permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
#                 return True
#             self.logger.warning(f"Delete object permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
#             return False

#         if (user_role in self.WRITE_ROLES and user_department in self.ALLOWED_WRITE_DEPARTMENTS) or (hasattr(obj, 'created_by') and obj.created_by == request.user):
#             self.logger.debug(f"Write object permission granted for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
#             return True
#         self.logger.warning(f"Write object permission denied for {request.method} to user: {request.user}, role: {user_role}, department: {user_department} on object: {obj}")
#         return False
