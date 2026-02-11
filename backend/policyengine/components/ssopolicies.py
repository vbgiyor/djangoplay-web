import json
import logging
import zlib

from core.utils.redis_client import redis_client
from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from policyengine.components.actions import MODEL_ROLE_PERMISSIONS

logger = logging.getLogger(__name__)

EXCLUDED_APPS = {'apidocs', 'audit', "core", "devtools", "frontend", "policyengine", "utilities", }
EXCLUDED_MODELS = {"featureflag", "employee", "memberprofile", "signup_request"}

# Define default apps you want permissions for
DEFAULT_APP_LABELS = ['entities', 'locations', 'industries', 'fincore', 'invoices',
                      'teamcentral', 'helpdesk']
CACHE_TIMEOUT = 86400  # 1 day


def setup_role_based_group(role_code: str):
    """
    Create or update a group with permissions based on role_code using MODEL_ROLE_PERMISSIONS.
    Only assigns permissions where the role is explicitly mentioned.
    """
    cache_key = f"group_setup:{role_code}"
    cached = redis_client.get(cache_key)
    if cached:
        logger.debug(f"Using cached group for role={role_code}")
        try:
            return Group.objects.get(name=role_code)
        except Group.DoesNotExist:
            redis_client.delete(cache_key)

    group, _ = Group.objects.get_or_create(name=role_code)

    # Clear all existing permissions (optional: keep if you want incremental updates)
    group.permissions.clear()

    assigned_perms = []

    # 1. First, handle permissions from MODEL_ROLE_PERMISSIONS
    for model_name, action_map in MODEL_ROLE_PERMISSIONS.items():
        for action, roles in action_map.items():
            if role_code not in roles:
                continue

            try:
                # Find model class from all installed apps
                model = None
                for app_config in apps.get_app_configs():
                    if app_config.label in EXCLUDED_APPS:
                        continue
                    try:
                        model = app_config.get_model(model_name)
                        break
                    except LookupError:
                        continue

                if not model:
                    logger.warning(f"Model '{model_name}' not found in any app.")
                    continue

                content_type = ContentType.objects.get_for_model(model)
                codename = f"{action}_{model._meta.model_name}"
                permission, _ = Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type,
                    defaults={'name': f"Can {action} {model._meta.verbose_name}"}
                )
                group.permissions.add(permission)
                assigned_perms.append({
                    "codename": codename,
                    "content_type_id": content_type.id,
                    "name": permission.name
                })

                logger.debug(f"Assigned {codename} to group {role_code}")

            except Exception as e:
                logger.exception(f"Error assigning permission {action}_{model_name} for role {role_code}: {str(e)}")

    # 2. Add special permissions for 'apidocs' app like view_redoc and view_swagger
    for perm_codename in ['view_redoc', 'view_swagger']:
        try:
            content_type = ContentType.objects.get(app_label='apidocs', model='apidocs')  # Adjust model name if needed
            permission, _ = Permission.objects.get_or_create(
                codename=perm_codename,
                content_type=content_type,
                defaults={'name': f"Can {perm_codename.replace('_', ' ')}"}
            )
            group.permissions.add(permission)
            assigned_perms.append({
                'codename': perm_codename,
                'content_type_id': content_type.id,
                'name': permission.name
            })
            logger.debug(f"Assigned {perm_codename} to group {role_code}")

        except Exception as e:
            logger.error(f"Error assigning special permission {perm_codename} for role {role_code}: {str(e)}")

    # 3. Add default permissions for apps (like view_ permission for all models in DEFAULT_APP_LABELS)
    for app_label in DEFAULT_APP_LABELS:
        try:
            app_config = apps.get_app_config(app_label)
            for model in app_config.get_models():
                if model._meta.model_name in EXCLUDED_MODELS:
                    continue

                content_type = ContentType.objects.get_for_model(model)
                codename = f"view_{model._meta.model_name}"
                permission, _ = Permission.objects.get_or_create(
                    content_type=content_type,
                    codename=codename,
                    defaults={'name': f"Can view {model._meta.verbose_name}"}
                )
                group.permissions.add(permission)
                assigned_perms.append({
                    'codename': codename,
                    'content_type_id': content_type.id,
                    'name': permission.name
                })
                logger.debug(f"Assigned view permission for {model._meta.model_name} in {app_label}")

        except Exception as e:
            logger.error(f"Error setting up permissions for app {app_label}: {str(e)}")

    # Cache the group and permissions data
    try:
        redis_client.setex(cache_key, CACHE_TIMEOUT, zlib.compress(json.dumps({
            'group_name': role_code,
            'permissions': assigned_perms
        }).encode()))
        logger.info(f"Cached permissions for role={role_code} in Redis")
    except Exception as e:
        logger.error(f"Failed to cache permissions for {role_code}: {str(e)}")

    logger.info("Role-based group setup completed")
    return group
