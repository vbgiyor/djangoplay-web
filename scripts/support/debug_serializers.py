import logging
import os

from django.apps import apps
from django.core.wsgi import get_wsgi_application
from rest_framework import serializers

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paystream.settings')
application = get_wsgi_application()

logger = logging.getLogger(__name__)

def check_serializer_fields(serializer_class, path='', seen=None):
    if seen is None:
        seen = set()
    issues = []

    logger.info(f"Inspecting serializer: {serializer_class.__name__}, fields: {list(serializer_class._declared_fields.keys())}")

    # Avoid infinite recursion for nested serializers
    serializer_key = f"{serializer_class.__module__}.{serializer_class.__name__}"
    if serializer_key in seen:
        return issues
    seen.add(serializer_key)

    # Check declared fields
    for field_name, field in serializer_class._declared_fields.items():
        field_path = f"{path}.{field_name}" if path else field_name
        default_value = getattr(field, 'default', serializers.empty)
        required = getattr(field, 'required', False)

        # Check explicit required=True and default
        if required and default_value is not serializers.empty:
            issues.append(f"Issue in {serializer_class.__name__} at {field_path}: 'required=True' and 'default={default_value}' are both set")

        # Check nested serializers
        if isinstance(field, serializers.Serializer):
            issues.extend(check_serializer_fields(field.__class__, field_path, seen))
        elif isinstance(field | (serializers.ListSerializer, serializers.SerializerMethodField)):
            if hasattr(field, 'child') and isinstance(field.child, serializers.Serializer):
                issues.extend(check_serializer_fields(field.child.__class__, field_path, seen))

    # Check model fields for implicit required=True
    if hasattr(serializer_class, 'Meta') and hasattr(serializer_class.Meta, 'model'):
        model = serializer_class.Meta.model
        for field_name in serializer_class().get_fields():
            field = serializer_class().fields[field_name]
            field_path = f"{path}.{field_name}" if path else field_name
            try:
                model_field = model._meta.get_field(field_name)
                # Model field is not nullable and has a default
                if not model_field.null and not model_field.blank and model_field.has_default():
                    if not hasattr(field, 'required') or field.required:  # Implicitly required
                        issues.append(
                            f"Issue in {serializer_class.__name__} at {field_path}: "
                            f"Model field has default={model_field.default} and is not nullable, "
                            f"implying required=True"
                        )
            except model._meta.model.DoesNotExist:
                continue  # Skip fields not in model

    return issues

def inspect_serializers():
    issues = []
    for app_config in apps.get_app_configs():
        logger.debug(f"Inspecting app: {app_config.name}")
        for name, obj in app_config.__dict__.items():
            if isinstance(obj, type) and issubclass(obj, serializers.Serializer) and obj != serializers.Serializer:
                logger.debug(f"Checking serializer: {app_config.name}.{name}")
                issues.extend(check_serializer_fields(obj, path=f"{app_config.name}.{name}"))
    return issues

if __name__ == "__main__":
    import django
    from django.conf import settings
    django.setup()
    issues = inspect_serializers()
    if issues:
        print("Found issues:")
        for issue in issues:
            print(issue)
    else:
        print("No issues found.")
