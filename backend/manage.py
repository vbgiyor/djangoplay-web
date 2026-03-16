#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.
For Linux/Windows:
python manage.py runserver_plus "${BIND_HOST}:${BIND_PORT}"
or
python manage.py runserver "${BIND_HOST}:${BIND_PORT}"
"""
import os
import sys
import warnings

# ---------------------------------------------------------------------
# Silence "Accessing the database during app initialization is discouraged"
# RuntimeWarning raised by django-simple-history (and similar).
# ---------------------------------------------------------------------
warnings.filterwarnings(
    "ignore",
    message=r"Accessing the database during app initialization is discouraged.*",
    category=RuntimeWarning,
)

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault(
    "PYTHONWARNINGS",
    "ignore::UserWarning:multiprocessing.resource_tracker"
)


def main():
    """Run administrative tasks."""
    # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paystream.settings')
    os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    os.getenv('DJANGO_SETTINGS_MODULE', 'paystream.settings.dev')
)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
