from django.conf import settings


def satellite_urls(request):
    return {
        "idp_home_url": settings.IDP_HOME_URL,
        "idp_home_ws_url": settings.IDP_HOME_WS_URL,
        "app_prefix": settings.APP_NAME_PREFIX,
    }
