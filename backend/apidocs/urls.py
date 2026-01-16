import logging

from apidocs.views import CustomSpectacularRedocView, CustomSpectacularSwaggerView, PersonalAPIStatsView, PublicAPIStatsView
from apidocs.views.spectacular import CustomSpectacularAPIView
from django.urls import path
from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)

app_name = 'apidocs'

@extend_schema(exclude=True)
class CustomSpectacularAPIViewDecorated(CustomSpectacularAPIView):
    pass

@extend_schema(exclude=True)
class CustomSpectacularSwaggerViewDecorated(CustomSpectacularSwaggerView):
    pass

@extend_schema(exclude=True)
class CustomSpectacularRedocViewDecorated(CustomSpectacularRedocView):
    pass


urlpatterns = [
    path("schema/", CustomSpectacularAPIViewDecorated.as_view(), name="schema"),
    path("swagger/", CustomSpectacularSwaggerViewDecorated.as_view(url_name="apidocs:schema"), name="swagger-ui"),
    path("redoc/", CustomSpectacularRedocViewDecorated.as_view(url_name="apidocs:schema"), name="redoc"),

    # Public
    path('apistats/public', PublicAPIStatsView.as_view(), name='api-stats-public'),

    # Personal (requires login + flag)
    path('apistats/private', PersonalAPIStatsView.as_view(), name='api-stats-private'),
]
