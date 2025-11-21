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
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_expiration = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    longitude = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    place = models.CharField(max_length=300)
    radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, help_text="Service radius in kilometers")
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

# models.py - Add this to your OrderAssign model

from django.db import models
from django.utils import timezone
from django.core.cache import cache
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

class OrderAssign(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='assigned_orders')
    delivery_boy = models.ForeignKey('DeliveryBoy', on_delete=models.CASCADE, related_name='assigned_orders')
    assigned_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, default='ASSIGNED', choices=[
        ('ASSIGNED', 'Assigned'),
        ('ACCEPTED', 'Accepted'),
        ('PICKED', 'Picked'),
        ('ON_THE_WAY', 'On the way'),
        ('DELIVERED', 'Delivered'),
        ('RETURNED', 'Returned'),
        ('REJECTED', 'Rejected')
    ])
    is_rejected = models.BooleanField(default=False)
    is_accepted = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(
        'DeliveryBoy', 
        related_name='accepted_orders', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL
    )
    delivery_charge = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Delivery charge for this order"
    )

    class Meta:
        ordering = ['-assigned_at']
        verbose_name = 'Order Assignment'
        verbose_name_plural = 'Order Assignments'

    def __str__(self):
        return f"Order {self.order.order_id} assigned to {self.delivery_boy.name}"

    def get_location_name(self, latitude, longitude):
        """
        Convert latitude and longitude to a human-readable location name
        Uses caching to avoid repeated API calls for the same coordinates
        """
        if not latitude or not longitude:
            return None
        
        # Create cache key from coordinates (rounded to 4 decimal places for grouping nearby locations)
        lat_rounded = round(float(latitude), 4)
        lon_rounded = round(float(longitude), 4)
        cache_key = f"location_{lat_rounded}_{lon_rounded}"
        
        # Check if location name is already cached
        cached_location = cache.get(cache_key)
        if cached_location:
            return cached_location
        
        try:
            # Initialize geocoder with user agent
            geolocator = Nominatim(user_agent="fastbag_app", timeout=10)
            
            # Reverse geocode to get location name
            location = geolocator.reverse(f"{latitude}, {longitude}", language='en')
            
            if location:
                # Extract a clean location name
                address = location.raw.get('address', {})
                
                # Build location string from address components
                location_parts = []
                
                # Add locality/suburb/village
                for key in ['suburb', 'neighbourhood', 'village', 'town']:
                    if address.get(key):
                        location_parts.append(address[key])
                        break
                
                # Add city
                for key in ['city', 'municipality', 'county']:
                    if address.get(key):
                        location_parts.append(address[key])
                        break
                
                # Add state
                if address.get('state'):
                    location_parts.append(address['state'])
                
                location_name = ', '.join(location_parts) if location_parts else location.address
                
                # Cache the result for 30 days
                cache.set(cache_key, location_name, 60 * 60 * 24 * 30)
                
                return location_name
            
            return None
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Geocoding timeout/service error for ({latitude}, {longitude}): {e}")
            return None
        except Exception as e:
            print(f"Geocoding error for ({latitude}, {longitude}): {e}")
            return None

    def save(self, *args, **kwargs):
        """Override save to update status flags"""
        if self.status == 'ACCEPTED':
            self.is_accepted = True
            self.is_rejected = False
        elif self.status == 'REJECTED':
            self.is_rejected = True
            self.is_accepted = False
        
        super().save(*args, **kwargs)

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