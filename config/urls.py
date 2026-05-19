# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

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

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.accounts.views import (
    DeleteCredentialView,
    GenerateCredentialView,
    ImportCredentialView,
    StoreSignedCredentialView,
    VCManagementView,
)
from apps.poller.views import poll_list

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", poll_list, name="poll_list"),
    path("", include("apps.core.urls")),
    path("", include("apps.poller.urls")),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("login/", RedirectView.as_view(pattern_name="oidc_authentication_init"), name="login"),
    path("logout/", RedirectView.as_view(pattern_name="oidc_logout"), name="logout"),
    path("credentials/", VCManagementView.as_view(), name="vc_management"),
    path("credentials/store-signed/", StoreSignedCredentialView.as_view(), name="store_signed_credential"),
    path("credentials/generate/", GenerateCredentialView.as_view(), name="generate_credential"),
    path("credentials/delete/", DeleteCredentialView.as_view(), name="delete_credential"),
    path("credentials/import/", ImportCredentialView.as_view(), name="import_credential"),
]

if settings.DEBUG:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
