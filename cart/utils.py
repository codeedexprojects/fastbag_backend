"""
FCM Notification Utility for sending Firebase Cloud Messaging notifications
"""
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import os


def initialize_firebase():
    """
    Initialize Firebase Admin SDK
    Call this once in your Django app's apps.py or __init__.py
    """
    if not firebase_admin._apps:
        try:
            cred_path = os.path.join(settings.BASE_DIR, 'firebase_credentials.json')
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully")
        except Exception as e:
            print(f"Failed to initialize Firebase: {str(e)}")


def send_fcm_notification(fcm_token, title, body, data=None, notification_type='general'):
    """
    Generic function to send FCM notification
    
    Args:
        fcm_token (str): The FCM token of the recipient
        title (str): Notification title
        body (str): Notification body message
        data (dict): Additional data payload
        notification_type (str): Type of notification for analytics
    
    Returns:
        str: Message ID if successful, None if failed
    """
    if not fcm_token:
        print("No FCM token provided")
        return None

    try:
        # Prepare data payload
        notification_data = data or {}
        notification_data['type'] = notification_type
        notification_data['click_action'] = 'FLUTTER_NOTIFICATION_CLICK'

        # Create the notification message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=notification_data,
            token=fcm_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='ic_notification',
                    color='#4CAF50',
                    sound='default',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1,
                    ),
                ),
            ),
        )

        # Send the message
        response = messaging.send(message)
        print(f"Successfully sent FCM notification: {response}")
        return response

    except Exception as e:
        print(f"Failed to send FCM notification: {str(e)}")
        return None


def send_order_placed_notification(user, order_id, final_amount):
    """Send notification to user when order is placed"""
    if not hasattr(user, 'fcm_token') or not user.fcm_token:
        return None

    return send_fcm_notification(
        fcm_token=user.fcm_token,
        title="Order Placed Successfully! 🎉",
        body=f"Your order {order_id} has been placed. Total: ₹{final_amount}",
        data={
            "order_id": order_id,
            "amount": str(final_amount),
        },
        notification_type='order_placed'
    )


def send_new_order_notification(vendor, order_id, customer_name, final_amount):
    """Send notification to vendor when new order is received"""
    if not hasattr(vendor, 'fcm_token') or not vendor.fcm_token:
        return None

    return send_fcm_notification(
        fcm_token=vendor.fcm_token,
        title="New Order Received! 🔔",
        body=f"Order {order_id} from {customer_name}. Amount: ₹{final_amount}",
        data={
            "order_id": order_id,
            "customer_name": customer_name,
            "amount": str(final_amount),
        },
        notification_type='new_order'
    )


def send_order_status_notification(user, order_id, status, message=None):
    """Send notification when order status changes"""
    if not hasattr(user, 'fcm_token') or not user.fcm_token:
        return None

    status_messages = {
        'confirmed': 'Your order has been confirmed! ✅',
        'processing': 'Your order is being processed 📦',
        'shipped': 'Your order has been shipped! 🚚',
        'delivered': 'Your order has been delivered! 🎁',
        'cancelled': 'Your order has been cancelled ❌',
    }

    default_message = message or status_messages.get(status, f'Order status updated to {status}')

    return send_fcm_notification(
        fcm_token=user.fcm_token,
        title="Order Status Update",
        body=f"Order {order_id}: {default_message}",
        data={
            "order_id": order_id,
            "status": status,
        },
        notification_type='order_status'
    )


def send_delivery_notification(user, order_id, delivery_pin):
    """Send notification with delivery PIN"""
    if not hasattr(user, 'fcm_token') or not user.fcm_token:
        return None

    return send_fcm_notification(
        fcm_token=user.fcm_token,
        title="Out for Delivery! 🚚",
        body=f"Order {order_id} is out for delivery. Your PIN: {delivery_pin}",
        data={
            "order_id": order_id,
            "delivery_pin": delivery_pin,
        },
        notification_type='out_for_delivery'
    )


def send_payment_notification(user, order_id, payment_status, amount):
    """Send notification about payment status"""
    if not hasattr(user, 'fcm_token') or not user.fcm_token:
        return None

    status_messages = {
        'success': f'Payment successful! ✅ Amount: ₹{amount}',
        'failed': f'Payment failed! ❌ Amount: ₹{amount}',
        'pending': f'Payment pending. Amount: ₹{amount}',
    }

    return send_fcm_notification(
        fcm_token=user.fcm_token,
        title="Payment Update",
        body=f"Order {order_id}: {status_messages.get(payment_status, 'Payment status updated')}",
        data={
            "order_id": order_id,
            "payment_status": payment_status,
            "amount": str(amount),
        },
        notification_type='payment_status'
    )


def send_bulk_notifications(fcm_tokens, title, body, data=None):
    """
    Send notification to multiple devices at once
    
    Args:
        fcm_tokens (list): List of FCM tokens
        title (str): Notification title
        body (str): Notification body
        data (dict): Additional data payload
    
    Returns:
        BatchResponse: Response containing success and failure counts
    """
    if not fcm_tokens:
        return None

    try:
        notification_data = data or {}
        notification_data['click_action'] = 'FLUTTER_NOTIFICATION_CLICK'

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=notification_data,
            tokens=fcm_tokens,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='ic_notification',
                    color='#4CAF50',
                    sound='default',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1,
                    ),
                ),
            ),
        )

        response = messaging.send_multicast(message)
        print(f"Successfully sent {response.success_count} messages")
        if response.failure_count > 0:
            print(f"Failed to send {response.failure_count} messages")
        
        return response

    except Exception as e:
        print(f"Failed to send bulk notifications: {str(e)}")
        return None