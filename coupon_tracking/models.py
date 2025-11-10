from django.db import models
from django.conf import settings
from cart.models import Coupon,Checkout
from users.models import CustomUser

class UserCouponUsage(models.Model):
    coupon = models.ForeignKey('users.Coupon', on_delete=models.CASCADE, related_name='usages')  # Use string reference
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_coupon_usages')
    checkout = models.ForeignKey('cart.Checkout', on_delete=models.CASCADE, related_name='user_coupon_usages')
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('coupon', 'user', 'checkout')

