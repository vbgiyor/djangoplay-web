from django import template
from django.conf import settings

register = template.Library()

@register.filter
def get_action_name(cl, action):
    """
    Returns the display name of the action.
    If action has 'short_description', return it, else fallback to method name.
    """
    try:
        return cl.get_action_name(action)
    except Exception:
        if hasattr(action, 'short_description'):
            return action.short_description
        return str(action)

@register.filter
def dict_get(d, key):
    """Safely get a value from a dictionary. Returns empty string if key not present."""
    if d is None:
        return ''
    return d.get(key, '')


@register.filter
def region_country_id(region_id):
    """
    Given a Region ID, return the related Country ID.
    """
    from locations.models import CustomRegion
    try:
        region = CustomRegion.objects.select_related('country').get(id=region_id)
        return region.country.id if region.country else ''
    except CustomRegion.DoesNotExist:
        return ''

@register.filter
def get_app_display_name(app_label):
    return settings.APP_DISPLAY_NAMES.get(app_label, app_label.title())
