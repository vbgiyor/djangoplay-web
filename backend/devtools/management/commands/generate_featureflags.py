# devtools/management/commands/generate_featureflags.py
from django.apps import apps
from django.core.management.base import BaseCommand
from policyengine.models import FeatureFlag

ACTIONS = ["list", "create", "update", "destroy", "retrieve"]
EXCLUDED_APPS = {
    "admin", "contenttypes", "sessions", "auth",
    "core", "utilities", "policyengine", "devtools"
}
EXCLUDED_MODELS = {"featureflag"}

# === CUSTOM FLAGS (model_action style) ===
CUSTOM_FLAGS = [
    {
        "key": "apidocs_stats_view",
        "description": "Enable API Statistics Dashboard (public or personal view)",
        "enabled_globally": False,
        "roles": ["DJGO", "CEO", "SSO"],
        "users": []  # No specific users
    },
    {
        "key": "apidocs_stats_csv",
        "description": "Allow CSV export from API Statistics Dashboard",
        "enabled_globally": False,
        "roles": ["DJGO", "CEO", "SSO"],
        "users": []
    },
]

class Command(BaseCommand):
    help = "Generate default feature flags for all models/actions + custom flags"

    def handle(self, *args, **kwargs):
        created = 0

        # === 1. Model-Action Flags ===
        for model in apps.get_models():
            app_label = model._meta.app_label.lower()
            model_name = model.__name__.lower()
            if app_label in EXCLUDED_APPS or model_name in EXCLUDED_MODELS:
                continue

            for action in ACTIONS:
                key = f"{app_label}_{model_name}_{action}"
                obj, was_created = FeatureFlag.objects.get_or_create(
                    key=key,
                    defaults={
                        'description': f"Allow {action} on {model_name}",
                        'enabled_globally': False,
                        'roles': []  # JSONField → list is OK
                    }
                )
                if was_created:
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"Created: {key}"))

        # === 2. Custom Flags (SAFE for JSONField + M2M) ===
        for flag_data in CUSTOM_FLAGS:
            key = flag_data["key"]
            defaults = {
                'description': flag_data["description"],
                'enabled_globally': flag_data["enabled_globally"],
                'roles': flag_data["roles"],  # JSONField → list is fine
            }

            obj, was_created = FeatureFlag.objects.update_or_create(
                key=key,
                defaults=defaults
            )

            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created custom: {key}"))
            else:
                # Sync roles if changed
                if set(obj.roles) != set(flag_data["roles"]):
                    obj.roles = flag_data["roles"]
                    obj.save(update_fields=['roles'])
                    self.stdout.write(self.style.WARNING(f"Updated roles for: {key}"))

            # === HANDLE ManyToMany: users ===
            # Clear and re-add (only if users list changes)
            desired_users = flag_data["users"]
            if desired_users:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                users = User.objects.filter(username__in=desired_users)
                if users.exists():
                    obj.users.set(users)
            else:
                obj.users.clear()  # No users

        self.stdout.write(self.style.SUCCESS(f"Done. Total created/updated: {created}"))
