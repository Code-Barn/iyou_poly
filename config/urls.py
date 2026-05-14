"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.accounts.views import VCManagementView
from apps.poller.views import poll_list

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", poll_list, name="poll_list"),
    path("", include("apps.core.urls")),
    path("", include("apps.poller.urls")),
    path("__debug__/", include("debug_toolbar.urls")),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("login/", RedirectView.as_view(pattern_name="oidc_authentication_init"), name="login"),
    path("logout/", RedirectView.as_view(pattern_name="oidc_logout"), name="logout"),
    path("credentials/", VCManagementView.as_view(), name="vc_management"),
]
