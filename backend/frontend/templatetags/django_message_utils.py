from django import template

register = template.Library()

@register.filter
def bootstrap_alert(level):
    mapping = {
        "error": "danger",
        "warning": "warning",
        "success": "success",
        "info": "info",
    }
    return mapping.get(level, "secondary")
