from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404


def license_file_view(request):
    project_root = Path(settings.BASE_DIR).parent  # go one level up
    license_path = project_root / "LICENSE"

    if not license_path.exists():
        raise Http404("License file not found")

    return FileResponse(license_path.open("rb"), content_type="text/plain")
