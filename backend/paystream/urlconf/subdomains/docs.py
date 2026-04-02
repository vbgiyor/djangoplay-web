import os

from django.conf import settings
from django.urls import re_path
from django.views.static import serve

# Use the dynamic path from settings (populated from your YAML/Env)
DOCS_ROOT = settings.DOCS_ROOT

def serve_docs(request, path=""):
    """
    Custom view to handle documentation routing.
    - Serves index.html for the root.
    - Serves existing physical files (view.html, images, etc.)
    - Falls back to view.html for client-side routing of markdown files.
    """
    # Clean leading/trailing slashes
    path = path.strip("/")

    # Handle the legacy /docs/ path if it's passed through
    if path == "docs":
        path = ""

    # 1. If user hits the root (empty path), serve index.html
    if not path:
        return serve(request, "index.html", document_root=DOCS_ROOT)

    # 2. Check if the physical file exists in the docs root
    full_path = os.path.join(DOCS_ROOT, path)
    if os.path.exists(full_path):
        return serve(request, path, document_root=DOCS_ROOT)

    # 3. Otherwise, fallback to view.html which handles markdown via JS hash
    return serve(request, "view.html", document_root=DOCS_ROOT)

urlpatterns = [
    # Static assets folders (explicitly mapped for performance)
    re_path(r"^dist/(?P<path>.*)$", serve, {"document_root": os.path.join(DOCS_ROOT, "dist")}),
    # Use (?P<path>.*)? to make the named group 'path' optional.
    # This allows {% host_url 'docs' host 'docs' %} to match with no arguments.
    re_path(r"^(?P<path>.*)?$", serve_docs, name='docs'),
]
