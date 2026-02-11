from collections import defaultdict

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from policyengine.components.actions import MODEL_ROLE_PERMISSIONS
from policyengine.components.ssopolicies import (
    DEFAULT_APP_LABELS,
    EXCLUDED_APPS,
    EXCLUDED_MODELS,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Grant or revoke permission(s) for a user by email"

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, required=True, help="User email")
        parser.add_argument("--perm", type=str, help="Specific permission codename")
        parser.add_argument("--app", type=str, help="Comma-separated app labels")
        parser.add_argument("--model", type=str, help="Comma-separated model names")
        parser.add_argument(
            "--actions",
            type=str,
            help="Comma-separated actions: view, add, change, delete",
        )
        parser.add_argument(
            "--allow",
            type=str,
            choices=["True", "False"],
            required=True,
            help="Grant or revoke",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview permissions without applying changes",
        )
        parser.add_argument(
            "--summary",
            action="store_true",
            help="Print permission summary",
        )
        parser.add_argument(
            "--feature-flag",
            type=str,
            help="Feature flag key to enable/disable for the user",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        allow = options["allow"] == "True"
        dry_run = options["dry_run"]
        self._summary = {"granted": 0, "revoked": 0, "skipped": 0}

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User with email '{email}' not found"))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY-RUN] ' if dry_run else ''}"
                f"{'Granting' if allow else 'Revoking'} permissions for {email}"
            )
        )

        perm_codename = options.get("perm")
        app_labels = self._split(options.get("app"))
        model_names = self._split(options.get("model"))
        actions = self._split(options.get("actions")) or ["view"]

        if perm_codename:
            self._assign_custom_permission(user, perm_codename, allow, dry_run)
        elif app_labels or model_names:
            self._assign_permissions_for_scope(
                user, app_labels, model_names, actions, allow, dry_run
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "No --perm / --app / --model specified. Applying defaults."
                )
            )
            self._assign_all_default_permissions(user, allow, dry_run)

        if options.get("feature_flag"):
            self._handle_feature_flag(
                user=user,
                flag_key=options["feature_flag"],
                allow=allow,
                dry_run=dry_run,
            )

        self._print_final_permissions(user)

        if options.get("summary"):
            self._print_summary()

    # ─────────────────────────────────────────────
    # Permission helpers
    # ─────────────────────────────────────────────

    def _assign_custom_permission(self, user, codename, allow, dry_run):
        # content_type = ContentType.objects.get_for_model(Permission)
        content_type = ContentType.objects.get(
            app_label="apidocs",
        )

        permission, _ = Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={"name": f"Can {codename.replace('_', ' ')}"},
        )
        self._assign_permission(user, permission, allow, dry_run)

    def _assign_permissions_for_scope(
        self, user, app_labels, model_names, actions, allow, dry_run
    ):
        matched_models = set()

        for app_label in app_labels:
            try:
                app_config = apps.get_app_config(app_label)
                for model in app_config.get_models():
                    if model._meta.model_name not in EXCLUDED_MODELS:
                        matched_models.add(model)
            except LookupError:
                self.stderr.write(self.style.ERROR(f"App '{app_label}' not found"))

        for model_name in model_names:
            for app in apps.get_app_configs():
                try:
                    model = app.get_model(model_name)
                    matched_models.add(model)
                    break
                except LookupError:
                    continue

        for model in matched_models:
            content_type = ContentType.objects.get_for_model(model)
            for action in actions:
                codename = f"{action}_{model._meta.model_name}"
                permission, _ = Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type,
                    defaults={
                        "name": f"Can {action} {model._meta.verbose_name}"
                    },
                )
                self._assign_permission(user, permission, allow, dry_run)

    def _assign_permission(self, user, permission, allow, dry_run):
        full_name = f"{permission.content_type.app_label}.{permission.codename}"
        has_direct = permission in user.user_permissions.all()

        if allow:
            if has_direct:
                self._summary["skipped"] += 1
                return
            if not dry_run:
                user.user_permissions.add(permission)
            self._summary["granted"] += 1
            self.stdout.write(
                self.style.SUCCESS(f"{'Would grant' if dry_run else 'Granted'} {full_name}")
            )
        else:
            if not has_direct:
                self._summary["skipped"] += 1
                return
            if not dry_run:
                user.user_permissions.remove(permission)
            self._summary["revoked"] += 1
            self.stdout.write(
                self.style.SUCCESS(f"{'Would revoke' if dry_run else 'Revoked'} {full_name}")
            )

    def _assign_all_default_permissions(self, user, allow, dry_run):
        for model_name, actions in MODEL_ROLE_PERMISSIONS.items():
            for app in apps.get_app_configs():
                if app.label in EXCLUDED_APPS:
                    continue
                try:
                    model = app.get_model(model_name)
                except LookupError:
                    continue

                content_type = ContentType.objects.get_for_model(model)
                for action in actions:
                    codename = f"{action}_{model._meta.model_name}"
                    permission, _ = Permission.objects.get_or_create(
                        codename=codename,
                        content_type=content_type,
                        defaults={
                            "name": f"Can {action} {model._meta.verbose_name}"
                        },
                    )
                    self._assign_permission(user, permission, allow, dry_run)

        for app_label in DEFAULT_APP_LABELS:
            try:
                app = apps.get_app_config(app_label)
            except LookupError:
                continue

            for model in app.get_models():
                if model._meta.model_name in EXCLUDED_MODELS:
                    continue

                content_type = ContentType.objects.get_for_model(model)
                codename = f"view_{model._meta.model_name}"
                permission, _ = Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type,
                    defaults={
                        "name": f"Can view {model._meta.verbose_name}"
                    },
                )
                self._assign_permission(user, permission, allow, dry_run)
        try:
            content_type = ContentType.objects.get(
                app_label="apidocs",
                model="apirequestlog",
            )
            for codename in ["view_redoc", "view_swagger"]:
                permission, _ = Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type,
                    defaults={"name": f"Can {codename.replace('_', ' ')}"},
                )
                self._assign_permission(user, permission, allow, dry_run)
        except ContentType.DoesNotExist:
            self.stderr.write("apidocs content type not found")

    # ─────────────────────────────────────────────
    # Feature flag handling
    # ─────────────────────────────────────────────

    def _handle_feature_flag(self, *, user, flag_key, allow, dry_run):
        from policyengine.models import FeatureFlag

        try:
            flag = FeatureFlag.objects.get(key=flag_key)
        except FeatureFlag.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"FeatureFlag '{flag_key}' not found"))
            return

        enabled = user in flag.users.all()

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"[DRY-RUN] Would {'enable' if allow else 'disable'} "
                    f"'{flag_key}' for {user.email}"
                )
            )
            return

        if allow and not enabled:
            flag.users.add(user)
            self.stdout.write(self.style.SUCCESS(f"Enabled '{flag_key}'"))
        elif not allow and enabled:
            flag.users.remove(user)
            self.stdout.write(self.style.SUCCESS(f"Disabled '{flag_key}'"))

    # ─────────────────────────────────────────────
    # Output helpers
    # ─────────────────────────────────────────────

    def _print_final_permissions(self, user):
        perms = sorted(user.get_all_permissions())
        grouped = defaultdict(list)
        for perm in perms:
            app, code = perm.split(".", 1)
            grouped[app].append(code)

        self.stdout.write(self.style.SUCCESS("Final permissions:"))
        for app in sorted(grouped):
            self.stdout.write(f"  {app}: {', '.join(sorted(grouped[app]))}")

    def _print_summary(self):
        self.stdout.write(self.style.NOTICE("Permission Summary"))
        for key, val in self._summary.items():
            self.stdout.write(f"  {key.capitalize()}: {val}")

    @staticmethod
    def _split(value):
        if not value:
            return []
        return [v.strip() for v in value.split(",") if v.strip()]

# from collections import defaultdict

# from django.apps import apps
# from django.contrib.auth.models import Permission
# from django.contrib.contenttypes.models import ContentType
# from django.core.management.base import BaseCommand
# from policyengine.components.actions import MODEL_ROLE_PERMISSIONS
# from policyengine.components.ssopolicies import DEFAULT_APP_LABELS, EXCLUDED_APPS, EXCLUDED_MODELS
# from users.contracts.identity import get_identity_snapshot
# from users.services.identity_query_service import IdentityQueryService


# class Command(BaseCommand):
#     help = "Grant or revoke permission(s) for an employee by email"

#     def add_arguments(self, parser):
#         parser.add_argument("--email", type=str, required=True, help="Email of the employee")
#         parser.add_argument("--perm", type=str, help="Specific permission codename (e.g., view_swagger)")
#         parser.add_argument("--app", type=str, help="Comma-separated app labels")
#         parser.add_argument("--model", type=str, help="Comma-separated model names")
#         parser.add_argument("--actions", type=str, help="Comma-separated actions: view, add, change, delete")
#         parser.add_argument("--allow", type=str, choices=["True", "False"], required=True, help="Grant or revoke")
#         parser.add_argument("--dry-run", action="store_true", help="Preview permissions without applying changes")
#         parser.add_argument("--summary", action="store_true", help="Print a summary of permission actions")
#         parser.add_argument("--feature-flag", type=str,help="Feature flag key (e.g. apidocs_stats_view). Use with --allow True/False to enable/disable.")

#     def handle(self, *args, **options):
#         email = options["email"]
#         perm_codename = options.get("perm")
#         app_labels = options.get("app")
#         model_names = options.get("model")
#         allow_permission = options["allow"] == "True"
#         actions = options.get("actions")
#         dry_run = options.get("dry_run", False)
#         self._summary = {"granted": 0, "revoked": 0, "skipped": 0}

#         try:
#             from django.contrib.auth import get_user_model
#             User = get_user_model()
#             employee = User.objects.get(email__iexact=email)

#             app_labels = [a.strip() for a in app_labels.split(",")] if app_labels else []
#             model_names = [m.strip() for m in model_names.split(",")] if model_names else []
#             action_types = [a.strip() for a in actions.split(",")] if actions else ["view"]

#             self.stdout.write(self.style.SUCCESS(
#                 f"{'[DRY-RUN] ' if dry_run else ''}{'Granting' if allow_permission else 'Revoking'} permissions for {email}..."
#             ))

#             if perm_codename:
#                 self._assign_custom_permission(employee, perm_codename, allow_permission, dry_run)

#             elif app_labels or model_names:
#                 self._assign_permissions_for_specified(employee, app_labels, model_names, action_types, allow_permission, dry_run)

#             else:
#                 self.stdout.write(self.style.WARNING("No --perm, --app, or --model specified. Using default apps/models."))
#                 self._assign_all_default_permissions(employee, allow_permission, dry_run)

#             current_permissions = sorted(employee.get_all_permissions())
#             grouped_perms = defaultdict(list)
#             for perm in current_permissions:
#                 app, codename = perm.split(".", 1)
#                 grouped_perms[app].append(codename)

#             self.stdout.write(self.style.SUCCESS(f"Final permissions for {email}:"))
#             for app in sorted(grouped_perms.keys()):
#                 perms = ", ".join(sorted(grouped_perms[app]))
#                 self.stdout.write(f"  - {app}: {perms}")

#             if options.get("summary"):
#                 self.stdout.write(self.style.NOTICE("Permission Summary:"))
#                 for key, count in self._summary.items():
#                     self.stdout.write(f"  {key.capitalize()}: {count}")

#             if options.get("feature_flag"):
#                 self._handle_feature_flag(
#                     employee=employee,
#                     flag_key=options["feature_flag"],
#                     allow=allow_permission,
#                     dry_run=dry_run
#                 )
#                 return

#         except User.DoesNotExist:
#             self.stdout.write(self.style.ERROR(f"Employee with email '{email}' not found"))
#         except Exception as e:
#             self.stdout.write(self.style.ERROR(f"Unexpected error: {str(e)}"))

#     def _assign_custom_permission(self, employee, codename, allow, dry_run):
#         # Use apidocs app for view_redoc and view_swagger permissions
#         if codename in ['view_redoc', 'view_swagger']:
#             content_type = ContentType.objects.get(app_label='apidocs', model='')
#         else:
#             # Fallback to Permission model content type for other permissions
#             content_type = ContentType.objects.get_for_model(Permission)

#         # Create or fetch the permission
#         permission, _ = Permission.objects.get_or_create(
#             codename=codename,
#             content_type=content_type,
#             defaults={"name": f"Can {codename.replace('_', ' ')}"}
#         )

#         self._assign_permission(employee, permission, content_type.app_label, allow, dry_run)

#     def _assign_permissions_for_specified(self, employee, app_labels, model_names, actions, allow, dry_run):
#         matched_models = []

#         # Load models by app
#         for app_label in app_labels:
#             try:
#                 app_config = apps.get_app_config(app_label)
#                 for model in app_config.get_models():
#                     if model._meta.model_name in EXCLUDED_MODELS:
#                         continue
#                     matched_models.append(model)
#             except LookupError:
#                 self.stdout.write(self.style.ERROR(f"❌ App '{app_label}' not found"))

#         # Load models by model name
#         for model_name in model_names:
#             found = False
#             for app in apps.get_app_configs():
#                 for model in app.get_models():
#                     if model._meta.model_name == model_name.lower():
#                         matched_models.append(model)
#                         found = True
#                         break
#                 if found:
#                     break
#             if not found:
#                 self.stdout.write(self.style.ERROR(f"❌ Model '{model_name}' not found in any app"))

#         seen = set()
#         granted = 0

#         for model in matched_models:
#             if model in seen:
#                 continue
#             seen.add(model)
#             content_type = ContentType.objects.get_for_model(model)

#             for action in actions:
#                 codename = f"{action}_{model._meta.model_name}"
#                 permission, _ = Permission.objects.get_or_create(
#                     codename=codename,
#                     content_type=content_type,
#                     defaults={"name": f"Can {action} {model._meta.verbose_name}"}
#                 )
#                 self._assign_permission(employee, permission, content_type.app_label, allow, dry_run)
#                 granted += 1

#         self.stdout.write(self.style.SUCCESS(
#             f"{'[DRY-RUN] ' if dry_run else ''}{'Would grant' if dry_run and allow else 'Would revoke' if dry_run else 'Granted' if allow else 'Revoked'} {granted} permissions based on app/model/actions"
#         ))

#     def _assign_permission(self, employee, permission, app_label, allow, dry_run):
#         full_perm = f"{app_label}.{permission.codename}"
#         user_perms = employee.user_permissions.all()
#         groups = employee.groups.all()
#         has_permission = full_perm in employee.get_all_permissions()
#         directly_assigned = permission in user_perms

#         if allow:
#             if not directly_assigned:
#                 if dry_run:
#                     self.stdout.write(self.style.NOTICE(f"🔍 Would grant '{full_perm}'"))
#                 else:
#                     employee.user_permissions.add(permission)
#                     self.stdout.write(self.style.SUCCESS(f"✅ Granted '{full_perm}'"))
#                     self._summary["granted"] += 1
#             else:
#                 self.stdout.write(self.style.WARNING(f"⚠️ Already has '{full_perm}' (direct)"))
#                 self._summary["skipped"] += 1
#         else:
#             removed = False

#             if directly_assigned:
#                 if dry_run:
#                     self.stdout.write(self.style.NOTICE(f"🔍 Would revoke '{full_perm}' (direct)"))
#                     self._summary["revoked"] += 1
#                 else:
#                     employee.user_permissions.remove(permission)
#                     self.stdout.write(self.style.SUCCESS(f"❌ Revoked '{full_perm}' (direct)"))
#                 removed = True

#             for group in groups:
#                 if permission in group.permissions.all():
#                     if dry_run:
#                         self.stdout.write(self.style.NOTICE(f"🔍 Would revoke '{full_perm}' from group '{group.name}'"))
#                     else:
#                         group.permissions.remove(permission)
#                         self.stdout.write(self.style.SUCCESS(f"❌ Revoked '{full_perm}' from group '{group.name}'"))
#                         self._summary["revoked"] += 1
#                         removed = True

#             if not removed:
#                 if has_permission:
#                     self.stdout.write(self.style.WARNING(f"⚠️ Has '{full_perm}' via group — group permission not found for removal"))
#                 else:
#                     self.stdout.write(self.style.WARNING(f"⚠️ Did not have '{full_perm}'"))
#                 self._summary["skipped"] += 1

#     def _assign_all_default_permissions(self, employee, allow, dry_run):
#         assigned = 0

#         for model_name, action_map in MODEL_ROLE_PERMISSIONS.items():
#             for action in action_map.keys():
#                 try:
#                     model = None
#                     for app_config in apps.get_app_configs():
#                         if app_config.label in EXCLUDED_APPS:
#                             continue
#                         try:
#                             model = app_config.get_model(model_name)
#                             break
#                         except LookupError:
#                             continue

#                     if not model:
#                         continue

#                     content_type = ContentType.objects.get_for_model(model)
#                     codename = f"{action}_{model._meta.model_name}"
#                     permission, _ = Permission.objects.get_or_create(
#                         codename=codename,
#                         content_type=content_type,
#                         defaults={"name": f"Can {action} {model._meta.verbose_name}"}
#                     )
#                     self._assign_permission(employee, permission, content_type.app_label, allow, dry_run)
#                     assigned += 1

#                 except Exception as e:
#                     self.stdout.write(self.style.ERROR(f"Error assigning {action}_{model_name}: {str(e)}"))

#         for app_label in DEFAULT_APP_LABELS:
#             try:
#                 app_config = apps.get_app_config(app_label)
#                 for model in app_config.get_models():
#                     if model._meta.model_name in EXCLUDED_MODELS:
#                         continue
#                     content_type = ContentType.objects.get_for_model(model)
#                     codename = f"view_{model._meta.model_name}"
#                     permission, _ = Permission.objects.get_or_create(
#                         codename=codename,
#                         content_type=content_type,
#                         defaults={'name': f"Can view {model._meta.verbose_name}"}
#                     )
#                     self._assign_permission(employee, permission, content_type.app_label, allow, dry_run)
#                     assigned += 1

#             except Exception as e:
#                 self.stdout.write(self.style.ERROR(f"Error in app '{app_label}': {str(e)}"))

#         self.stdout.write(self.style.SUCCESS(
#             f"{'[DRY-RUN] ' if dry_run else ''}{'Would grant' if dry_run and allow else 'Would revoke' if dry_run else 'Granted' if allow else 'Revoked'} {assigned} default permissions"
#         ))

#     def _handle_feature_flag(self, employee, flag_key, allow, dry_run):
#         from policyengine.models import FeatureFlag

#         try:
#             flag = FeatureFlag.objects.get(key=flag_key)
#         except FeatureFlag.DoesNotExist:
#             self.stdout.write(self.style.ERROR(f"FeatureFlag '{flag_key}' not found"))
#             return

#         already_enabled = employee in flag.users.all()
#         action = "enable" if allow else "disable"

#         if dry_run:
#             self.stdout.write(
#                 self.style.NOTICE(f"[DRY-RUN] Would {action} '{flag_key}' for {employee.email}")
#             )
#             return

#         if allow:
#             if already_enabled:
#                 self.stdout.write(self.style.WARNING(f"'{flag_key}' already enabled for {employee.email}"))
#             else:
#                 flag.users.add(employee)
#                 self.stdout.write(self.style.SUCCESS(f"Enabled '{flag_key}' for {employee.email}"))
#         else:
#             if not already_enabled:
#                 self.stdout.write(self.style.WARNING(f"'{flag_key}' not enabled for {employee.email}"))
#             else:
#                 flag.users.remove(employee)
#                 self.stdout.write(self.style.SUCCESS(f"Disabled '{flag_key}' for {employee.email}"))
