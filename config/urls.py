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
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.accounts.views import (
    DeleteCredentialView,
    DIDLoginView,
    GenerateCredentialView,
    GenerateDIDAndVCView,
    ImportCredentialView,
    RegisterView,
    UpdateVCNameView,
    VCManagementView,
)
from apps.poller.views import poll_list

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", poll_list, name="poll_list"),  # Home page - poll list
    path("", include("apps.core.urls")),
    path("", include("apps.poller.urls")),
    path("__debug__/", include("debug_toolbar.urls")),  # Django Debug Toolbar
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("login/", include("mozilla_django_oidc.urls")), # Override login with OIDC
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "login/did/",
        DIDLoginView.as_view(),
        name="did_login",
    ),

]
