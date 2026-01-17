import logging

from django.contrib.admin import AdminSite
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from utilities.context_processors.report_bug import report_bug_context

logger = logging.getLogger(__name__)



class PaystreamAdminSite(AdminSite):
    site_header = _("DjangoPlay Administration")
    site_title = _("DjangoPlay Admin")
    name = 'console'
    index_title = _("Welcome to DjangoPlay Admin")
    login_template = 'account/site_pages/login.html'
    logout_template = 'account/site_pages/logout.html'

    # from utilities.constants.template_registry import TemplateRegistry
    # login_template = TemplateRegistry.CONSOLE_LOGIN
    # logout_template = TemplateRegistry.CONSOLE_LOGOUT

    def get_urls(self):
        urls = super().get_urls()
        # Remove all changelist URLs
        return [
            url for url in urls
            if not (hasattr(url, 'name') and url.name and url.name.endswith('_changelist'))
        ]

    def login(self, request, extra_context=None):
        if request.user.is_authenticated:
            return redirect('console_dashboard')  # Redirect to dashboard after login
        return redirect('account_login')

    def index(self, request, extra_context=None):
        """
        Redirect /console/ to /console/dashboard/ instead of rendering index.html.
        """
        logger.debug(f"Redirecting /console/ to /console/dashboard/ for user {request.user}")
        return redirect('console_dashboard')

    def admin_view(self, view, cacheable=False):
        def inner(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('account_login')  # Redirect unauthenticated users
            return view(request, *args, **kwargs)
        return inner

    def each_context(self, request):
        context = super().each_context(request)
        context.update(report_bug_context(request))  # Add bug report context
        context['login_url'] = reverse('account_login') # Use allauth's login URL
        return context

    def get_app_list(self, request, app_label=None):
        """
        Customize the app list to group related models and control visibility.
        """
        app_list = super().get_app_list(request, app_label)

        # Custom app groupings
        users_app = {
            'name': 'Users',
            'app_label': 'users',
            'app_url': '#',
            'has_module_perms': request.user.has_module_perms('users'),
            'models': [],
        }
        locations_app = {
            'name': 'Locations',
            'app_label': 'locations',
            'app_url': '#',
            'has_module_perms': request.user.has_module_perms('locations'),
            'models': [],
        }
        industries_app = {
            'name': 'Industries',
            'app_label': 'industries',
            'app_url': '#',
            'has_module_perms': request.user.has_module_perms('industries'),
            'models': [],
        }
        fincore_app = {
            'name': 'Business Contact & Tax Info',
            'app_label': 'fincore',
            'app_url': '#',
            'has_module_perms': request.user.has_module_perms('fincore'),
            'models': [],
        }
        entities_app = {
            'name': 'Businesses',
            'app_label': 'entities',
            'app_url': '#',
            'has_module_perms': request.user.has_module_perms('entities'),
            'models': [],
        }
        invoices_app = {
            'name': 'Invoices',
            'app_label': 'invoices',
            'app_url': '#',
            'has_module_perms': request.user.has_module_perms('invoices'),
            'models': [],
        }
        audit_app = {
            'name': 'Audit Logging',
            'app_label': 'audit',
            'app_url': '#',
            'has_module_perms': request.user.has_module_perms('audit'),
            'models': [],
        }


        # Process app list
        new_app_list = []
        for app in app_list:
            # Collect models for apps
            if app['app_label'] == 'users':
                users_app['models'].extend(app['models'])
            elif app['app_label'] == 'locations':
                locations_app['models'].extend(app['models'])
            elif app['app_label'] == 'industries':
                industries_app['models'].extend(app['models'])
            elif app['app_label'] == 'fincore':
                fincore_app['models'].extend(app['models'])
            elif app['app_label'] == 'entities':
                entities_app['models'].extend(app['models'])
            elif app['app_label'] == 'invoices':
                invoices_app['models'].extend(app['models'])
            elif app['app_label'] == 'audit':
                audit_app['models'].extend(app['models'])

            else:
                # Keep other apps as they are
                new_app_list.append(app)

        # Add custom apps to the list if they have models
        for custom_app in [users_app, locations_app, industries_app, fincore_app, entities_app, invoices_app]:
            if custom_app['models']:
                custom_app['models'].sort(key=lambda x: x['name'])
                # Always assign app_url, even if the first model has no admin_url
                first_model_url = custom_app['models'][0].get('admin_url', '#')
                custom_app['app_url'] = first_model_url
                new_app_list.append(custom_app)

        new_app_list.sort(key=lambda x: x['name'])
        return new_app_list

admin_site = PaystreamAdminSite(name='console')

