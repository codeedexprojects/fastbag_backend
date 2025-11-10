from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, UserRegNotification

@receiver(post_save, sender=CustomUser)
def create_registration_notification(sender, instance, created, **kwargs):
    if created:  
        # print(f"Signal triggered for {instance.mobile_number}") 
        UserRegNotification.objects.create(
            user=instance,
            notification_type='registration',
            message=f"New user registered with mobile: {instance.mobile_number}"
        )