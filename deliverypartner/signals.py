from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

@receiver(post_save, sender=apps.get_model('cart', 'Order'))
def notify_delivery_boys_on_order_created(sender, instance, created, **kwargs):
    if created:
        DeliveryBoy = apps.get_model('deliverypartner', 'DeliveryBoy')
        DeliveryNotification = apps.get_model('deliverypartner', 'DeliveryNotification')
        
        message = f"A new order (Order ID: {instance.order_id}) has been placed."

        for boy in DeliveryBoy.objects.filter(is_active=True):
            DeliveryNotification.objects.create(
                delivery_boy=boy,
                order=instance,  
                message=message
            )
