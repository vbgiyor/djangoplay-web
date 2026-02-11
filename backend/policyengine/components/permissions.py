import logging

from core.utils.redis_client import redis_client
from policyengine.commons.base import get_user_role, is_user_active
from policyengine.components.actions import ACTION_PERMISSIONS, MODEL_ROLE_PERMISSIONS
from policyengine.components.roles import PERMISSION_ROLES
from policyengine.models import FeatureFlag
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

# Set of apps/models to exclude from feature flag checks
EXCLUDED_APPS = {"policyengine", "core", "utitlities", "users"}
EXCLUDED_MODELS = {"featureflag"}  # lowercase model names


class ActionBasedPermission(BasePermission):

    """
    Generic permission class to restrict specific actions to certain roles,
    optionally gated by a feature flag.
    """

    def __init__(
        self,
        allowed_actions=None,
        allowed_roles=None,
        feature_flag_key: str = None,
        model_name: str = None,
    ):
        self.allowed_actions = allowed_actions or {}
        self.allowed_roles = allowed_roles or set()
        self.feature_flag_key = feature_flag_key
        self.model_name = model_name

    # -------------------------------------------------
    # Feature flag evaluation
    # -------------------------------------------------
    def _is_feature_enabled_for_user(self, feature_key: str, user) -> bool:
        """
        Checks if a feature flag is enabled for a user.
        Uses Redis cache for performance.
        """
        cache_key = f"featureflag:{feature_key}:user:{user.id}"
        cached = redis_client.get(cache_key)

        if cached is not None:
            return cached == b"1"

        try:
            flag = FeatureFlag.objects.get(key=feature_key)
            enabled = flag.is_enabled_for(user)
        except FeatureFlag.DoesNotExist:
            enabled = False

        redis_client.setex(cache_key, 300, int(enabled))  # cache 5 min
        return enabled

    # -------------------------------------------------
    # Permission entrypoint
    # -------------------------------------------------
    def has_permission(self, request, view) -> bool:
        logger.debug(
            "[Permission] Checking access user=%s action=%s",
            request.user,
            getattr(view, "action", None),
        )

        if not request.user.is_authenticated:
            logger.warning("[Permission] Denied: unauthenticated user")
            return False

        if not is_user_active(request.user):
            logger.warning("[Permission] Denied: inactive user %s", request.user)
            return False

        if request.user.is_superuser:
            logger.info("[Permission] Granted: superuser %s", request.user)
            return True

        # Explicit Swagger guard
        if view.action == "swagger" and not request.user.has_perm("view_swagger"):
            logger.warning(
                "[Permission] Denied: user %s lacks view_swagger",
                request.user,
            )
            return False

        # Feature flag gate (dynamic)
        if self.feature_flag_key:
            if not self._is_feature_enabled_for_user(
                self.feature_flag_key, request.user
            ):
                logger.warning(
                    "[Permission] Denied: feature flag %s OFF for user %s",
                    self.feature_flag_key,
                    request.user,
                )
                return False

        user_role = get_user_role(request.user)
        if not user_role:
            logger.warning(
                "[Permission] Denied: no role assigned for user %s",
                request.user,
            )
            return False

        # -------------------------------------------------
        # HARD SYSTEM GUARDS (non-negotiable)
        # -------------------------------------------------
        model_name = None
        try:
            model_name = view.queryset.model.__name__.lower()
        except Exception:
            pass

        app_label = None
        try:
            app_label = view.queryset.model._meta.app_label.lower()
        except Exception:
            pass

        # 🔒 USERS APP + MEMBERPROFILE = SUPERUSER ONLY
        if (
            app_label == "users"
            or model_name == "memberprofile"
        ):
            if not request.user.is_superuser:
                logger.warning(
                    "[Permission] Denied: superuser-only model app=%s model=%s user=%s",
                    app_label,
                    model_name,
                    request.user,
                )

        # -------------------------------------------------
        # Resolve model + action permissions
        # -------------------------------------------------
        model_name = self.model_name
        if not model_name:
            try:
                model_name = view.queryset.model.__name__.lower()
            except Exception:
                model_name = None

        action_roles = self.allowed_actions.get(view.action)

        if not action_roles and model_name:
            model_actions = MODEL_ROLE_PERMISSIONS.get(model_name)
            if model_actions:
                action_roles = model_actions.get(view.action)

        if action_roles is None:
            action_roles = self.allowed_roles or PERMISSION_ROLES.get("read", [])

        if user_role in action_roles:
            logger.info(
                "[Permission] Granted: user=%s role=%s action=%s",
                request.user,
                user_role,
                view.action,
            )
            return True

        logger.warning(
            "[Permission] Denied: user=%s role=%s action=%s",
            request.user,
            user_role,
            view.action,
        )
        return False



def get_action_based_permissions(
    permission_classes,
    action_permissions=None,
    default_roles=None,
    view=None,
):
    """
    Factory to inject ActionBasedPermission with dynamic feature-flag keys.
    """
    normalized = [
        p.__class__ if isinstance(p, BasePermission) else p
        for p in permission_classes
    ]

    feature_flag_key = None
    model_name = None

    if view and getattr(view, "queryset", None) is not None:
        model = view.queryset.model
        model_name = model.__name__.lower()
        app_label = model._meta.app_label.lower()
        view_action = getattr(view, "action", None)

        if (
            app_label not in EXCLUDED_APPS
            and model_name not in EXCLUDED_MODELS
            and view_action
        ):
            feature_flag_key = f"{app_label}_{model_name}_{view_action}"

    return [
        p()
        if p is not ActionBasedPermission
        else ActionBasedPermission(
            allowed_actions=action_permissions or ACTION_PERMISSIONS,
            allowed_roles=default_roles or PERMISSION_ROLES.get("read", []),
            feature_flag_key=feature_flag_key,
            model_name=model_name,
        )
        for p in normalized
    ]


class ReDocPermission(BasePermission):

    """
    Grants access to ReDoc only to users with the `view_redoc` permission.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.has_perm("view_redoc")
        )


# import logging

# from core.utils.redis_client import redis_client
# from policyengine.models import FeatureFlag
# from rest_framework.permissions import BasePermission

# from ..commons.base import get_user_role, is_user_active
# from .actions import ACTION_PERMISSIONS, MODEL_ROLE_PERMISSIONS
# from .roles import PERMISSION_ROLES

# logger = logging.getLogger(__name__)

# # Set of apps/models to exclude from feature flag checks
# EXCLUDED_APPS = {"policyengine", "core", "utitlities"}
# EXCLUDED_MODELS = {"featureflag"}  # lowercase model names

# class ActionBasedPermission(BasePermission):

#     """Generic permission class to restrict specific actions to certain roles, optionally gated by a feature flag."""

#     def __init__(self, allowed_actions=None, allowed_roles=None, feature_flag_key: str = None, model_name: str = None):
#         self.allowed_actions = allowed_actions or {}
#         self.allowed_roles = allowed_roles or set()
#         self.feature_flag_key = feature_flag_key
#         self.model_name = model_name

#     def _is_feature_enabled_for_user(self, feature_key: str, user) -> bool:
#         """
#         Checks if a feature flag is enabled for a user.
#         Uses Redis cache for performance.
#         """
#         cache_key = f"featureflag:{feature_key}:user:{user.id}"
#         cached = redis_client.get(cache_key)

#         if cached is not None:
#             return cached == b"1"

#         try:
#             flag = FeatureFlag.objects.get(key=feature_key)
#             enabled = flag.is_enabled_for(user)
#         except FeatureFlag.DoesNotExist:
#             enabled = False

#         redis_client.setex(cache_key, 300, int(enabled))  # Cache for 5 minutes
#         return enabled

#     def has_permission(self, request, view) -> bool:
#         logger.debug(f"[Permission] Checking access for user={request.user} on action={view.action}")

#         if not request.user.is_authenticated:
#             logger.warning("[Permission] Denied: Unauthenticated user")
#             return False

#         if not is_user_active(request.user):
#             logger.warning(f"[Permission] Denied: Inactive user {request.user}")
#             return False

#         # Check if the user is a superuser
#         if request.user.is_superuser:
#             logger.info(f"[Permission] Granted: Superuser {request.user}")
#             return True

#         # Deny access to Swagger unless explicitly permitted
#         if view.action == 'swagger' and not request.user.has_perm('view_swagger'):
#             logger.warning(f"[Permission] Denied: User {request.user} does not have permission to view Swagger UI")
#             return False

#         if self.feature_flag_key:
#             if not self._is_feature_enabled_for_user(self.feature_flag_key, request.user):
#                 logger.warning(f"[Permission] Denied: Feature flag {self.feature_flag_key} is OFF for user {request.user}")
#                 return False
#             logger.debug(f"[Permission] Feature flag {self.feature_flag_key} is ON for user {request.user}")

#         user_role = get_user_role(request.user)
#         if not user_role:
#             logger.warning(f"[Permission] Denied: No role assigned for user {request.user}")
#             return False

#         if not request.user.has_perm('view_swagger'):
#             logger.warning(f"User {request.user} does not have 'view_swagger' permission.")
#             return False

#         # Dynamic fallback using model name
#         model_name = self.model_name
#         if not model_name:
#             try:
#                 model_name = view.queryset.model.__name__.lower()
#             except Exception:
#                 pass

#         # Use model-specific permissions if defined
#         action_roles = self.allowed_actions.get(view.action)
#         if not action_roles and model_name:
#             model_actions = MODEL_ROLE_PERMISSIONS.get(model_name)
#             if model_actions:
#                 action_roles = model_actions.get(view.action)

#         # Fallback to default role list
#         if action_roles is None:
#             action_roles = self.allowed_roles or PERMISSION_ROLES.get('read', [])

#         if user_role in action_roles:
#             logger.info(f"[Permission] Granted: User {request.user} with role={user_role} on {view.action}")
#             return True

#         logger.warning(f"[Permission] Denied: User {request.user} with role={user_role} not allowed for {view.action}")
#         return False



# def get_action_based_permissions(
#     permission_classes,
#     action_permissions=None,
#     default_roles=None,
#     view=None
# ):
#     normalized = [
#         p.__class__ if isinstance(p, BasePermission) else p
#         for p in permission_classes
#     ]

#     feature_flag_key = None
#     model_name = None

#     # Try to extract model info from view
#     if view and hasattr(view, 'queryset') and view.queryset is not None:
#         model = view.queryset.model
#         model_name = model.__name__.lower()
#         app_label = model._meta.app_label.lower()
#         view_action = getattr(view, 'action', None)

#         if app_label not in EXCLUDED_APPS and model_name not in EXCLUDED_MODELS and view_action:
#             # Generate dynamic key like: locations_customregion_create
#             feature_flag_key = f"{app_label}_{model_name}_{view_action}"

#     return [
#         p() if p != ActionBasedPermission
#         else ActionBasedPermission(
#             allowed_actions=action_permissions or ACTION_PERMISSIONS,
#             allowed_roles=default_roles or PERMISSION_ROLES.get('read', []),
#             feature_flag_key=feature_flag_key,
#             model_name=model_name
#         )
#         for p in normalized
#     ]


# class ReDocPermission(BasePermission):

#     """
#     Grants access to Redoc only to users with the `view_redoc` permission.
#     """

#     def has_permission(self, request, view):
#         if not request.user.is_authenticated:
#             return False
#         return request.user.has_perm("view_redoc")
