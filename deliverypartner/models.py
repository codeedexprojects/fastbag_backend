from django.db import models
from django.utils import timezone
from cart.models import Order
from django.core.validators import MinValueValidator



# Gender choices
GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
]

class DeliveryBoy(models.Model):
    name = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(max_length=255, unique=True, blank=True, null=True)
    password = models.CharField(max_length=128)
    photo = models.ImageField(upload_to='delivery_boys/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    vehicle_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    dob = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    aadhar_card_image = models.ImageField(upload_to='delivery_boys/aadhar_cards/', blank=True, null=True)
    driving_license_image = models.ImageField(upload_to='delivery_boys/driving_licenses/', blank=True, null=True)
    otp = models.CharField(max_length=6, blank=True, null=True)  # <-- ADD THIS
    otp_expiration = models.DateTimeField(blank=True, null=True)  # <-- AND THIS
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    longitude = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    place = models.CharField(max_length=300)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)


    def __str__(self):
        return self.name

    @property
    def age(self):
        from datetime import date
        if self.dob:
            today = date.today()
            age = today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
            return age
        return None

    def is_otp_valid(self):
        if self.otp_expiration and timezone.now() < self.otp_expiration:
            return True
        return False

class OrderAssign(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='assigned_orders')
    delivery_boy = models.ForeignKey(DeliveryBoy, on_delete=models.CASCADE, related_name='assigned_orders')
    assigned_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, default='ASSIGNED', choices=[
        ('ASSIGNED', 'Assigned'),
        ('ACCEPTED','Accepted'),
        ('PICKED', 'Picked'),
        ('ON_THE_WAY', 'On the way'),
        ('DELIVERED', 'Delivered'),
        ('RETURNED','Returned'),
        ('REJECTED','Rejected')
    ])
    is_rejected = models.BooleanField(default=False)
    is_accepted = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(DeliveryBoy, related_name='accepted_orders', null=True, blank=True, on_delete=models.SET_NULL)



    def __str__(self):
        return f"Order {self.order.id} assigned to {self.delivery_boy.name}"

class DeliveryNotification(models.Model):
    delivery_boy = models.ForeignKey(DeliveryBoy, on_delete=models.CASCADE, related_name="notifications")
    order = models.ForeignKey('cart.Order', on_delete=models.CASCADE, related_name="notifications",null=True)
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name="delivery_notifications", null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for Order {self.order.order_id} to {self.delivery_boy.name}"



class DeliveryCharges(models.Model):
    distance_from = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Starting distance in km"
    )
    distance_to = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Ending distance in km"
    )
    day_charge = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Delivery charge during day time"
    )
    night_charge = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Delivery charge during night time"
    )
    night_start_time = models.TimeField(
        default="22:00:00",
        help_text="Night rate starts from this time"
    )
    night_end_time = models.TimeField(
        default="06:00:00",
        help_text="Night rate ends at this time"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this charge rule is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delivery_charges'
        ordering = ['distance_from']
        verbose_name = 'Delivery Charge'
        verbose_name_plural = 'Delivery Charges'
    
    def __str__(self):
        return f"{self.distance_from}km - {self.distance_to}km: Day ₹{self.day_charge} | Night ₹{self.night_charge}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.distance_to <= self.distance_from:
            raise ValidationError("'Distance to' must be greater than 'Distance from'")