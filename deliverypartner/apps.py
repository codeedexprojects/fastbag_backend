from django.apps import AppConfig

class DeliverypartnerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'deliverypartner'

    def ready(self):
        import deliverypartner.signals