import ast
import os
from pathlib import Path

from django.core.management.base import BaseCommand

# ---------------------- Visitors ----------------------

class SerializerFieldVisitor(ast.NodeVisitor):

    """Scan DRF serializers for suspicious field definitions."""

    def __init__(self):
        self.bad_fields = []

    def visit_ClassDef(self, node):
        if any(
            isinstance(base, ast.Name) and base.id.endswith("Serializer")
            for base in node.bases
        ):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            self._check_field(target.id, stmt.value, node)
        self.generic_visit(node)

    def _check_field(self, field_name, value_node, class_node):
        if not isinstance(value_node, ast.Call):
            return

        # Detect field type
        if isinstance(value_node.func, ast.Attribute):
            field_type = value_node.func.attr
        elif isinstance(value_node.func, ast.Name):
            field_type = value_node.func.id
        else:
            field_type = None

        if not field_type:
            return

        kwargs = {kw.arg: kw.value for kw in value_node.keywords if kw.arg}

        # ---- Suspicious: default + required conflict ----
        if "default" in kwargs:
            required_val = kwargs.get("required")
            if not (
                isinstance(required_val, ast.Constant)
                and required_val.value is False
            ):
                self.bad_fields.append(
                    (class_node.name, field_name, field_type,
                     "Serializer field sets default but is required (or not explicitly required=False)")
                )


class ModelFieldVisitor(ast.NodeVisitor):

    """Scan Django models for risky field definitions."""

    def __init__(self):
        self.bad_fields = []

    def visit_ClassDef(self, node):
        if any(
            (isinstance(base, ast.Attribute) and base.attr == "Model")
            or (isinstance(base, ast.Name) and base.id == "Model")
            for base in node.bases
        ):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            self._check_field(target.id, stmt.value, node)
        self.generic_visit(node)

    def _check_field(self, field_name, value_node, class_node):
        if not isinstance(value_node, ast.Call):
            return

        if isinstance(value_node.func, ast.Attribute):
            field_type = value_node.func.attr
        elif isinstance(value_node.func, ast.Name):
            field_type = value_node.func.id
        else:
            field_type = None

        if not field_type:
            return

        kwargs = {kw.arg: kw.value for kw in value_node.keywords if kw.arg}

        # ---- Suspicious: default + blank conflict ----
        if "default" in kwargs:
            blank_val = kwargs.get("blank")
            if not (
                isinstance(blank_val, ast.Constant)
                and blank_val.value is True
            ):
                self.bad_fields.append(
                    (class_node.name, field_name, field_type,
                     "Model field sets default but is not blank=True (may cause required+default conflict in DRF)")
                )


class ViewVisitor(ast.NodeVisitor):

    """Scan DRF views for missing permissions/authentication."""

    def __init__(self):
        self.bad_views = []

    def visit_ClassDef(self, node):
        if any(
            isinstance(base, ast.Name) and base.id.endswith("View")
            or isinstance(base, ast.Name) and base.id.endswith("ViewSet")
            for base in node.bases
        ):
            has_permissions = any(
                isinstance(stmt, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "permission_classes"
                    for t in stmt.targets
                )
                for stmt in node.body
            )
            if not has_permissions:
                self.bad_views.append((node.name, "-", "-", "No permission_classes defined"))
        self.generic_visit(node)


# ---------------------- Command ----------------------

class Command(BaseCommand):
    help = "Scan serializers, models, and views for default/required/blank conflicts"

    def handle(self, *args, **options):
        base_dir = Path.cwd()
        issues = []

        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = Path(root) / file
                    try:
                        with open(filepath, encoding="utf-8") as f:
                            tree = ast.parse(f.read(), filename=str(filepath))

                        if "serializer" in file:
                            visitor = SerializerFieldVisitor()
                            visitor.visit(tree)
                            for bad in visitor.bad_fields:
                                issues.append((filepath, *bad))

                        elif "model" in file:
                            visitor = ModelFieldVisitor()
                            visitor.visit(tree)
                            for bad in visitor.bad_fields:
                                issues.append((filepath, *bad))

                        elif "view" in file:
                            visitor = ViewVisitor()
                            visitor.visit(tree)
                            for bad in visitor.bad_views:
                                issues.append((filepath, *bad))

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Failed to parse {filepath}: {e}")
                        )

        if not issues:
            self.stdout.write(
                self.style.SUCCESS("✅ No suspicious serializers, models, or views found.")
            )
        else:
            self.stdout.write(self.style.WARNING("⚠ Found issues:"))
            for filepath, cls, field, field_type, issue in issues:
                self.stdout.write(
                    f" - {filepath}: {cls}.{field} ({field_type}) → {issue}"
                )
