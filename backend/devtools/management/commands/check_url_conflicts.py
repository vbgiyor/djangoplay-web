import logging

from django.core.management.base import BaseCommand
from django.urls import get_resolver

logger = logging.getLogger('django.urls')

class Command(BaseCommand):
    help = 'Check for URL pattern conflicts'

    def handle(self, *args, **options):
        resolver = get_resolver()
        path_matches = {}

        # Iterate through all URL patterns
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'pattern'):
                path = str(pattern.pattern)
                if path in path_matches:
                    path_matches[path].append(pattern)
                else:
                    path_matches[path] = [pattern]

        # Log conflicts
        for path, patterns in path_matches.items():
            if len(patterns) > 1:
                logger.warning(
                    f"URL conflict detected for path: {path}. "
                    f"Matched patterns: {[str(p) for p in patterns]}"
                )
                self.stdout.write(
                    f"Warning: URL conflict for '{path}'. Patterns: {[str(p) for p in patterns]}",
                    style_func=self.style.WARNING
                )

        self.stdout.write("No URL conflicts found.", style_func=self.style.SUCCESS)
