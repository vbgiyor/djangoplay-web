import json
import os

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models


class Command(BaseCommand):
    help = 'Generate a JSON schema for all models in the specified Django app for database import'

    def add_arguments(self, parser):
        parser.add_argument('--app', required=True, help="Name of the Django app (e.g., 'invoices')")
        parser.add_argument('--output', required=True, help="Path to save the JSON schema file")

    def handle(self, *args, **options):
        app_label = options['app']
        output_path = options['output']

        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            self.stderr.write(f"App '{app_label}' not found")
            return

        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": f"{app_label} Database Import Schema",
            "type": "object",
            "properties": {}
        }

        # Iterate over all models in the app
        for model in app_config.get_models(include_auto_created=True):
            # Use the exact database table name from Meta.db_table, or model name as is if not specified
            table_name = model._meta.db_table or model.__name__
            schema["properties"][table_name] = {
                "type": "array",
                "items": self.generate_model_schema(model)
            }

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2)
            self.stdout.write(f"JSON schema successfully generated at {output_path}")
        except Exception as e:
            self.stderr.write(f"Failed to write JSON schema to {output_path}: {str(e)}")

    def generate_model_schema(self, model):
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        # Get all fields, including inherited ones
        for field in model._meta.get_fields(include_parents=True):
            # Skip reverse relations
            if isinstance(field, (models.ManyToOneRel, models.ManyToManyRel)):
                continue
            field_name = field.attname  # Use exact database column name
            schema["properties"][field_name] = self.get_field_schema(field)
            # Add to required if field is not nullable, not blank, and not auto-created
            if not field.null and not field.blank and not field.auto_created and not isinstance(field, models.ManyToManyField):
                schema["required"].append(field_name)

        return schema

    def get_field_schema(self, field):
        schema = {}

        # Handle field types
        if isinstance(field, models.AutoField):
            schema["type"] = "integer"
        elif isinstance(field, (models.CharField, models.TextField)):
            schema["type"] = ["string", "null"] if field.null else "string"
            if isinstance(field, models.CharField) and field.max_length:
                schema["maxLength"] = field.max_length
            if field.choices:
                schema["enum"] = [choice[0] for choice in field.choices] + ([None] if field.null else [])
        elif isinstance(field, models.BooleanField):
            schema["type"] = ["boolean", "null"] if field.null else "boolean"
        elif isinstance(field, (models.IntegerField, models.BigIntegerField, models.SmallIntegerField)):
            schema["type"] = ["integer", "null"] if field.null else "integer"
        elif nonullable_decimal_field(field):
            schema["type"] = "number"
            schema["multipleOf"] = 10 ** (-field.decimal_places)
        elif isinstance(field, models.DecimalField):
            schema["type"] = ["number", "null"]
            schema["multipleOf"] = 10 ** (-field.decimal_places)
        elif isinstance(field, models.DateField):
            schema["type"] = ["string", "null"] if field.null else "string"
            schema["format"] = "date"
        elif isinstance(field, models.DateTimeField):
            schema["type"] = ["string", "null"] if field.null else "string"
            schema["format"] = "date-time"
        elif isinstance(field, models.ForeignKey):
            schema["type"] = ["integer", "null"] if field.null else "integer"
        elif isinstance(field, models.ManyToManyField):
            schema["type"] = "array"
            schema["items"] = {"type": "integer"}
        else:
            schema["type"] = ["string", "null"] if field.null else "string"

        return schema

def nonullable_decimal_field(field):
    return isinstance(field, models.DecimalField) and not field.null
