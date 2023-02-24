from django.apps import AppConfig


class HappycreditsclientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'happycreditsclient'

    def ready(self):
        import happycreditsclient.signals
