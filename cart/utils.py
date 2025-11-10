"""
FCM Notification Utility for sending Firebase Cloud Messaging notifications
FIXED VERSION with proper error handling and improvements
"""
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import os
import logging
from users.models import CustomUser

# Set up logging
logger = logging.getLogger(__name__)


def initialize_firebase():
    """
    Initialize Firebase Admin SDK
    Call this once in your Django app's apps.py or __init__.py
    """
    if not firebase_admin._apps:
        try:
            cred_path = os.path.join(settings.BASE_DIR, 'firebase_credentials.json')
            
            # Check if credentials file exists
            if not os.path.exists(cred_path):
                logger.error(f"Firebase credentials file not found at: {cred_path}")
                return False
            
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            return False
    else:
        logger.info("Firebase Admin SDK already initialized")
        return True

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
    # Validate FCM token
    if not fcm_token:
        logger.warning("No FCM token provided")
        return None
    
    if not isinstance(fcm_token, str) or len(fcm_token.strip()) == 0:
        logger.warning(f"Invalid FCM token format: {fcm_token}")
        return None

    # Ensure Firebase is initialized
    if not firebase_admin._apps:
        logger.error("Firebase not initialized. Call initialize_firebase() first.")
        return None

    try:
        # Prepare data payload - ALL values must be strings
        notification_data = {}
        if data:
            for key, value in data.items():
                notification_data[str(key)] = str(value)
        
        notification_data['type'] = str(notification_type)
        notification_data['click_action'] = 'FLUTTER_NOTIFICATION_CLICK'

        # Create the notification message
        message = messaging.Message(
            notification=messaging.Notification(
                title=str(title),
                body=str(body),
            ),
            data=notification_data,
            token=fcm_token.strip(),
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
        logger.info(f"Successfully sent FCM notification: {response}")
        return response

    except messaging.UnregisteredError:
        logger.error(f"FCM token is invalid or unregistered: {fcm_token[:20]}...")
        return None
    except messaging.SenderIdMismatchError:
        logger.error("FCM sender ID mismatch - token belongs to different project")
        return None
    except messaging.QuotaExceededError:
        logger.error("FCM quota exceeded")
        return None
    except messaging.InvalidArgumentError as e:
        logger.error(f"Invalid FCM argument: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Failed to send FCM notification: {str(e)}", exc_info=True)
        return None

def send_order_placed_notification(user, order_id, final_amount):
    """Send notification to user when order is placed"""
    # Check if user has fcm_token attribute
    users = CustomUser.objects.get(pk=user)
    if not hasattr(users, 'fcm_token'):
        logger.warning(f"User {users} does not have fcm_token attribute")
        return None
    
    fcm_token = getattr(users, 'fcm_token', None)
    
    if not fcm_token:
        logger.warning(f"User {users} has no FCM token")
        return None

    return send_fcm_notification(
        fcm_token=fcm_token,
        title="Order Placed Successfully! 🎉",
        body=f"Your order {order_id} has been placed. Total: ₹{final_amount}",
        data={
            "order_id": str(order_id),
            "amount": str(final_amount),
        },
        notification_type='order_placed'
    )


def send_new_order_notification(vendor, order_id, customer_name, final_amount):
    """Send notification to vendor when new order is received"""
    # Check if vendor has fcm_token attribute
    if not hasattr(vendor, 'fcm_token'):
        logger.warning(f"Vendor {vendor.id} does not have fcm_token attribute")
        return None
    
    fcm_token = getattr(vendor, 'fcm_token', None)
    
    if not fcm_token:
        logger.warning(f"Vendor {vendor.id} has no FCM token")
        return None

    return send_fcm_notification(
        fcm_token=fcm_token,
        title="New Order Received! 🔔",
        body=f"Order {order_id} from {customer_name}. Amount: ₹{final_amount}",
        data={
            "order_id": str(order_id),
            "customer_name": str(customer_name),
            "amount": str(final_amount),
        },
        notification_type='new_order'
    )


def send_order_status_notification(user, order_id, status, message=None):
    """Send notification when order status changes"""
    if not hasattr(user, 'fcm_token'):
        logger.warning(f"User {user} does not have fcm_token attribute")
        return None
    
    fcm_token = getattr(user, 'fcm_token', None)
    
    if not fcm_token:
        logger.warning(f"User {user} has no FCM token")
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
        fcm_token=fcm_token,
        title="Order Status Update",
        body=f"Order {order_id}: {default_message}",
        data={
            "order_id": str(order_id),
            "status": str(status),
        },
        notification_type='order_status'
    )


def send_delivery_notification(user, order_id, delivery_pin):
    """Send notification with delivery PIN"""
    if not hasattr(user, 'fcm_token'):
        logger.warning(f"User {user} does not have fcm_token attribute")
        return None
    
    fcm_token = getattr(user, 'fcm_token', None)
    
    if not fcm_token:
        logger.warning(f"User {user} has no FCM token")
        return None

    return send_fcm_notification(
        fcm_token=fcm_token,
        title="Out for Delivery! 🚚",
        body=f"Order {order_id} is out for delivery. Your PIN: {delivery_pin}",
        data={
            "order_id": str(order_id),
            "delivery_pin": str(delivery_pin),
        },
        notification_type='out_for_delivery'
    )


def send_payment_notification(user, order_id, payment_status, amount):
    """Send notification about payment status"""
    if not hasattr(user, 'fcm_token'):
        logger.warning(f"User {user} does not have fcm_token attribute")
        return None
    
    fcm_token = getattr(user, 'fcm_token', None)
    
    if not fcm_token:
        logger.warning(f"User {user} has no FCM token")
        return None

    status_messages = {
        'success': f'Payment successful! ✅ Amount: ₹{amount}',
        'failed': f'Payment failed! ❌ Amount: ₹{amount}',
        'pending': f'Payment pending. Amount: ₹{amount}',
    }

    return send_fcm_notification(
        fcm_token=fcm_token,
        title="Payment Update",
        body=f"Order {order_id}: {status_messages.get(payment_status, 'Payment status updated')}",
        data={
            "order_id": str(order_id),
            "payment_status": str(payment_status),
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
    if not fcm_tokens or len(fcm_tokens) == 0:
        logger.warning("No FCM tokens provided for bulk notification")
        return None

    # Ensure Firebase is initialized
    if not firebase_admin._apps:
        logger.error("Firebase not initialized. Call initialize_firebase() first.")
        return None

    # Filter out invalid tokens
    valid_tokens = [token.strip() for token in fcm_tokens if token and isinstance(token, str) and len(token.strip()) > 0]
    
    if len(valid_tokens) == 0:
        logger.warning("No valid FCM tokens after filtering")
        return None

    try:
        # Prepare data payload - ALL values must be strings
        notification_data = {}
        if data:
            for key, value in data.items():
                notification_data[str(key)] = str(value)
        
        notification_data['click_action'] = 'FLUTTER_NOTIFICATION_CLICK'

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=str(title),
                body=str(body),
            ),
            data=notification_data,
            tokens=valid_tokens,
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
        logger.info(f"Successfully sent {response.success_count} messages")
        if response.failure_count > 0:
            logger.warning(f"Failed to send {response.failure_count} messages")
            # Log individual failures
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    logger.error(f"Failed to send to token {idx}: {resp.exception}")
        
        return response

    except Exception as e:
        logger.error(f"Failed to send bulk notifications: {str(e)}", exc_info=True)
        return None