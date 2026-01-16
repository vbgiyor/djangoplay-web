import os

from django.conf import settings
from django.http import FileResponse


def license_file_view(request):
    # Path to LICENSE.md in the repository root
    license_path = os.path.join(settings.BASE_DIR, 'LICENSE.md')
    return FileResponse(open(license_path, 'rb'), content_type='text/plain')
