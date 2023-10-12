from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

import floto.api.urls
import floto.dashboard.urls
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include((floto.api.urls, "floto.api"), namespace="api")),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('dashboard/',
         include((floto.dashboard.urls, "floto.dashboard"), namespace="dashboard")),
    path('oidc/', include('mozilla_django_oidc.urls')),
    path('', views.index),

]
