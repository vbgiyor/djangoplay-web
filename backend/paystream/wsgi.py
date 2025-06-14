import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

# Ensure the project directory is in the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paystream.settings')

application = get_wsgi_application()
