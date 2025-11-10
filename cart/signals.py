from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from cart.models import Order, Notification
from django.db import transaction

@receiver(post_save, sender=Order)
def order_placed_notification(sender, instance, created, **kwargs):
    if created:
        def on_commit():
            # Create internal notification
            Notification.objects.create(
                user=instance.user,
                title="Order Placed",
                message=f"Your order {instance.order_id} has been placed successfully."
            )

            # Send email to user
            if instance.user.email:
                send_mail(
                    subject="Order Confirmation",
                    message=f"Dear {instance.user.first_name},\n\nYour order {instance.order_id} has been successfully placed.\n\nThank you for shopping with us!",
                    from_email=None,
                    recipient_list=[instance.user.email],
                    fail_silently=False,
                )

        transaction.on_commit(on_commit)

@receiver(pre_save, sender=Order)
def order_status_update_notification(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        previous = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    if previous.order_status != instance.order_status:
        # Create internal notification
        Notification.objects.create(
            user=instance.user,
            title="Order Status Updated",
            message=f"Your order {instance.order_id} status changed from {previous.order_status} to {instance.order_status}."
        )

        # Send email update
        if instance.user.email:
            send_mail(
                subject="Order Status Update",
                message=f"Dear {instance.user.first_name},\n\nYour order {instance.order_id} status has changed from {previous.order_status} to {instance.order_status}.\n\nRegards,\nSupport Team",
                from_email=None,
                recipient_list=[instance.user.email],
                fail_silently=False,
            )
