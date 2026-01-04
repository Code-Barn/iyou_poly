from django.apps import AppConfig
from django.db.models import BigAutoField


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    default_auto_field = "django.db.models.BigAutoField"
