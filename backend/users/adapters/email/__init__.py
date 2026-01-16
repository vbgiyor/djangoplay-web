"""
Email infrastructure for adapters:
- EmailEngine
- TemplateResolver
- InlineImages
- Unsubscribe logic
"""
from .engine import EmailEngine
from .inline_images import InlineImageService
from .templates import TemplateResolver
from .unsubscribe import UnsubscribeService
