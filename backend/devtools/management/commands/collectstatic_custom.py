# In backend/paystream/management/commands/collectstatic.py
from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectStaticCommand


class Command(CollectStaticCommand):
    def get_path_to_ignore(self, path):
        # Ignore Django's admin/js files to prioritize jazzmin
        ignore_patterns = [
            'django/contrib/admin/static/admin/js/cancel.js',
            'django/contrib/admin/static/admin/js/popup_response.js',
        ]
        return any(pattern in path for pattern in ignore_patterns)

    def copy_file(self, path, prefixed_path, source_storage, **kwargs):
        if self.get_path_to_ignore(path):
            self.log(f"Skipping {path} due to exclusion rule", level=2)
            return
        super().copy_file(path, prefixed_path, source_storage, **kwargs)
