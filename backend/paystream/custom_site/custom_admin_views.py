import logging

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import reverse
from frontend.views.errors import custom_403, custom_404
from paystream.custom_site.admin_site import admin_site

logger = logging.getLogger(__name__)

@login_required
def console_dashboard(request):
    """
    View for the main dashboard at /console/dashboard/.
    """
    logger.debug(f"Rendering console_dashboard for user {request.user}")
    return TemplateResponse(request, 'account/dashboard.html', {
        'title': 'DjangoPlay Admin Dashboard',
        'site_header': admin_site.site_header,
        'site_title': admin_site.site_title,
    })

@login_required
def app_index_view(request):
    app_list = []
    for app_config in django_apps.get_app_configs():
        if app_config.name.startswith('django.') or not app_config.models:
            continue
        models = []
        for model in app_config.get_models():
            admin_instance = admin_site._registry.get(model)
            if not admin_instance:
                continue
            if request.user.has_perm(f"{app_config.label}.view_{model._meta.model_name}"):
                models.append({
                    'name': model._meta.verbose_name_plural,
                    'admin_url': reverse(f"admin:{app_config.label}_{model._meta.model_name}_changelist"),
                    'model_name': model._meta.model_name,
                    'icon': admin_site._registry[model].icon if hasattr(admin_site._registry[model], 'icon') else 'fas fa-circle',
                })
        if models:
            app_list.append({
                'name': app_config.verbose_name,
                'app_label': app_config.label,
                'app_url': reverse("admin_single_app", args=[app_config.label]),
                'models': models,
            })
    logger.debug(f"App list for user {request.user}: {app_list}")
    context = {
        'title': admin_site.index_title,
        'app_list': app_list,
        'site_header': admin_site.site_header,
        'site_title': admin_site.site_title,
    }
    return TemplateResponse(request, 'admin/app_index.html', context)

@login_required
def single_app_view(request, app_label):
    try:
        app_config = django_apps.get_app_config(app_label)
    except LookupError:
        logger.error(f"App {app_label} not found")
        display_name = settings.APP_DISPLAY_NAMES.get(app_label, app_label.title())
        return custom_404(request, app_label=app_label, app_display_name=display_name, exception=Http404("App not found"))
    models = []

    # Dynamically check if the app is enabled
    if not settings.APPS_READY.get(app_label, False):  # If app is marked as disabled (False)
        logger.error(f"Access to {app_label} is not allowed as it is under maintainance.")
        display_name = settings.APP_DISPLAY_NAMES.get(app_label, app_label.title())
        return custom_404(request, app_label=app_label, app_display_name=display_name, exception=Http404("App not found"))

    logger.debug(f"App label: {app_label}")
    logger.debug(f"App status (from APPS_READY): {settings.APPS_READY.get(app_label)}")

    user = request.user
    # Check if user is SSO based on role or employee_type
    member_profile = getattr(user, 'member_profile', None)
    is_sso_user = (
        member_profile and
        user.is_verified and
        member_profile.status.code == 'ACTV' and
        (user.role.code == 'SSO' or user.employee_type.code == 'SSO')
    )

    # Get Dynamic URL and App Name for current app
    parent_app_url = reverse('admin_single_app', args=[app_label])
    app_name = app_config.verbose_name

    # Define custom labels for models across all apps
    custom_labels = {
        # Users app models
        'users': {
            'employee': 'Employees',
            'passwordresetrequest': 'Password Reset Requests',
            'signuprequest': 'SignUp Requests',
        },
        'teamcentral': {
            'address': 'User Addresses',
            'department': 'Departments',
            'role': 'Roles',
            'employmentstatus': 'Employment Statuses',
            'employeetype': 'Employee Types',
            'memberstatus': 'Member Statuses',
            'memberprofile': 'Member Profiles',
            'leavetype': 'Leave Types',
            'leaveapplication': 'Leave Applications',
            'leavebalance': 'Leave Balances',
            'team': 'Teams',
        },
        # Helpdesk app models
        'helpdesk': {
            'bugreport': 'Bugs Catalogue',
            'supportticket': 'Support Requests',
            'fileupload': "Attachments"
        },
        # Locations app models
        'locations': {
            'globalregion': 'Continents',
            'customcountry': 'Countries',
            'customregion': 'Regions',
            'customsubregion': 'Sub-Regions',
            'customcity': 'Cities',
            'timezone': 'Timezones',
        },
        # Industries app models
        'industries': {
            'industry': 'Industries',
        },
        # Fincore app models
        'fincore': {
            'address': 'Business Addresses',
            'contact': 'Contacts',
            'taxprofile': 'Tax Profiles',
            'fincoreentitymapping': 'Entity Mappings',
        },
        # Entities app models
        'entities': {
            'entity': 'Business Catalogue',
        },
        # Invoices app models
        'invoices': {
            'invoice': 'Invoices & Billing',
        },
        # Invoices app models
        'audit': {
            'auditevent': 'Logging Journal',
        },
    }

    for model in app_config.get_models():
        admin_instance = admin_site._registry.get(model)
        if not admin_instance:
            continue
        # Allow access for superusers, staff, or users with view permission
        if (user.is_superuser or
                user.is_staff or
                user.has_perm(f"{app_label}.view_{model._meta.model_name}")):
            model_label = custom_labels.get(app_label, {}).get(model._meta.model_name, model._meta.verbose_name_plural)
            try:
                changelist_url = reverse(f"admin:{app_label}_{model._meta.model_name}_changelist")
            except Exception as e:
                logger.error(f"Failed to reverse changelist URL for {model}: {e}")
                continue

            models.append({
                'name': model_label,
                'admin_url': changelist_url,
                'model_name': model._meta.model_name,
                'icon': admin_instance.icon if hasattr(admin_instance, 'icon') else 'fas fa-circle',
                'is_read_only': is_sso_user,
            })

    if not models:
        logger.warning(f"No accessible models for app {app_label} for user {user}")
        return custom_403(request)


    logger.debug(f"Models for app {app_label} for user {user}: {models}")
    context = {
        'title': f"{app_config.verbose_name} Administration",
        'app_label': app_label,
        'app_name': app_name,
        'models': models,
        'site_header': admin_site.site_header,
        'site_title': admin_site.site_title,
        'is_read_only': is_sso_user,
        'parent_app_url': parent_app_url,
    }
    return TemplateResponse(request, 'admin/single_app.html', context)


@login_required
def custom_changelist_view(request, app_label, model_name):
    try:
        model = django_apps.get_model(app_label, model_name)
    except LookupError:
        return custom_404(request, app_label=app_label, exception=Http404("App is disabled / under maintainance."))

    admin_instance = admin_site._registry.get(model)
    if not admin_instance:
        return custom_404(request, app_label=app_label, exception=Http404("App is disabled / under maintainance."))

    # Check permission
    if not (request.user.is_superuser or
            request.user.is_staff or
            request.user.has_perm(f"{app_label}.view_{model._meta.model_name}")):
        return custom_403(request)


    # Get parent URL and app name
    parent_app_url = reverse('admin_single_app', args=[app_label])
    app_config = django_apps.get_app_config(app_label)
    app_name = app_config.verbose_name

    # Call original changelist view with extra context
    response = admin_instance.changelist_view(
        request,
        extra_context={
            'parent_app_url': parent_app_url,
            'app_name': app_name,
            'app_label': app_label,
        }
    )

    # If it's a TemplateResponse, update context
    if isinstance(response, TemplateResponse):
        response.context_data.update({
            'parent_app_url': parent_app_url,
            'app_name': app_name,
            'app_label': app_label,
        })

    return response
