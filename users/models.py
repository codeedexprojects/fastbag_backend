from django.db import models
from rest_framework.permissions import BasePermission
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.db import models
from django.conf import settings
import re
from django.core.exceptions import ValidationError
from vendors.models import Vendor
import uuid

class CustomUserManager(BaseUserManager):
    def _create_user(self, mobile_number, password=None, **extra_fields):
        if not mobile_number:
            raise ValueError('The Mobile Number field must be set')

        mobile_number = self.normalize_mobile_number(mobile_number)
        self.validate_mobile_number(mobile_number)

        user = self.model(mobile_number=mobile_number, **extra_fields)

        if password:
            self.validate_password(password)
            user.set_password(password)
        else:
            raise ValueError('The password must be set')

        user.save(using=self._db)
        return user

    def create_user(self, mobile_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(mobile_number, password, **extra_fields)

    def create_superuser(self, mobile_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(mobile_number, password, **extra_fields)

    def normalize_mobile_number(self, mobile_number):
        return mobile_number.strip()  

    def validate_mobile_number(self, mobile_number):
        if not re.match(r'^[0-9]{10}$', mobile_number):
            raise ValidationError("Invalid mobile number format. Must be 10 digits.")

    def validate_password(self, password):
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

    def authenticate(self, request, mobile_number, password=None):
        try:
            user = self.model.objects.get(mobile_number=mobile_number)
        except self.model.DoesNotExist:
            return None

        if user is not None and user.check_password(password):
            return user
        return None

class CustomUser(AbstractBaseUser, PermissionsMixin):
    mobile_number = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True, unique=True)
    is_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=6, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    permissions = models.JSONField(default=list, null=True, blank=True)
    favourite_vendors = models.ManyToManyField(Vendor, related_name="favorited_by", blank=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    groups = models.ManyToManyField(
        Group,
        related_name="customuser_groups",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    objects = CustomUserManager()
    USERNAME_FIELD = "mobile_number"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.mobile_number


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='addresses',
        on_delete=models.CASCADE,
    )
    address_type_choices = [
        ('Home', 'Home'),
        ('Work', 'Work'),
        ('Other','Other')
    ]
    address_type = models.CharField(max_length=20, choices=address_type_choices,null=True)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    address_name = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15,null=True)
    pincode = models.CharField(max_length=10)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    longitude = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)

    def __str__(self):
        return f"{self.address_line1}, {self.city}, {self.state}, {self.country}, {self.pincode}"

    class Meta:
        ordering = ['-created_at']

class UserRegNotification(models.Model):
    NOTIFICATION_TYPES = (
        ('registration', 'New Registration'),
        ('update', 'Profile Update'),
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='admin_notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='registration'
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.user.mobile_number}"

class FavoriteVendor(models.Model):
    user = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='favorite_vendor_links'
    )
    vendor = models.ForeignKey(
        'vendors.Vendor',
        on_delete=models.CASCADE,
        related_name='favorite_user_links'
    )

    class Meta:
        unique_together = ('user', 'vendor')

    def __str__(self):
        return f"{self.user} favorited {self.vendor}"


class BigBuyOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PREPARING', 'Preparing'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100, unique=True, editable=False)
    number_of_people = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    preferred_delivery_date = models.DateField()
    special_occasion = models.CharField(max_length=255, blank=True, null=True)
    diet_category = models.CharField(max_length=100, blank=True, null=True)
    additional_notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    cancel_reason = models.TextField(blank=True, null=True)


    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"BB-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"BigBuyOrder #{self.order_id} by {self.user} - [{self.status}]"


class BigBuyOrderItem(models.Model):
    order = models.ForeignKey(BigBuyOrder, related_name='order_items', on_delete=models.CASCADE)
    food_item = models.CharField(max_length=255)
    quantity_in_kg = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.food_item} - {self.quantity_in_kg}kg"


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=1)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True, related_name='coupons_created')
    is_new_customer = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'users_coupon'

    def __str__(self):
        return f"{self.code} - {self.vendor.business_name if self.vendor else 'Admin'}"


class UserLocation(models.Model):
    latitude = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    longitude = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    def __str__(self):
        return f"Location ({self.latitude}, {self.longitude})"