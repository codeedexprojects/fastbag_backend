from rest_framework import serializers
from deliverypartner.models import DeliveryBoy,OrderAssign,DeliveryNotification
from foodproduct.models import Dish
from .models import DeliveryCharges
from groceryproducts.models import GroceryProducts
from fashion.models import Clothing

class DeliveryBoySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryBoy
        fields = [
            'id',
            'name',
            'mobile_number',
            'email',
            'photo',
            'address',
            'vehicle_type',
            'vehicle_number',
            'gender',
            'dob',
            'is_active',
            'aadhar_card_image',
            'driving_license_image',
            'created_at',
            'updated_at',
            'longitude',
            'latitude',
            'place',
            'radius_km'
        ]

    def validate_mobile_number(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Mobile number must be at least 10 digits.")
        return value

    def validate_radius_km(self, value):
        if value < 0:
            raise serializers.ValidationError("Radius cannot be negative.")
        if value > 100:
            raise serializers.ValidationError("Radius cannot exceed 100 km.")
        return value

# class OTPLoginSerializer(serializers.Serializer):
#     email = serializers.EmailField()
#     otp = serializers.CharField(max_length=6)

# class OTPRequestSerializer(serializers.Serializer):
#     email = serializers.EmailField()

class OTPLoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)
    fcm_token = serializers.CharField(max_length=255,required=False)



class OTPRequestSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)


from cart.serializers import OrderSerializer

class OrderAssignSerializer(serializers.ModelSerializer):
    order_details = OrderSerializer(source='order', read_only=True)
    delivery_boy_details = DeliveryBoySerializer(source='delivery_boy', read_only=True)

    class Meta:
        model = OrderAssign
        fields = ['id','order', 'delivery_boy', 'assigned_at', 'status', 'order_details', 'delivery_boy_details']
        extra_kwargs = {
            'order': {'write_only': True},
            'delivery_boy': {'write_only': True}
        }


class DeliveryBoyOrderAssignSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    delivery_boy_name = serializers.CharField(source='delivery_boy.name', read_only=True)
    delivery_boy_number = serializers.CharField(source='delivery_boy.mobile_number', read_only=True)
    vendor_details = serializers.SerializerMethodField()
    user_details = serializers.SerializerMethodField()
    is_accepted = serializers.SerializerMethodField()
    is_rejected = serializers.SerializerMethodField()

    class Meta:
        model = OrderAssign
        fields = [
            'id', 'order_id', 'delivery_boy_name', 'delivery_boy_number',
            'status', 'assigned_at', 'vendor_details', 'user_details',
            'is_accepted', 'is_rejected'
        ]

    def get_vendor_details(self, obj):
        if obj.order and obj.order.checkout:
            items = obj.order.checkout.items.all()
            if items.exists():
                vendor = items.first().vendor
                if vendor:
                    return {
                        "name": vendor.business_name,
                        "address": vendor.address,
                        "landmark": vendor.business_landmark,
                        "city": vendor.city,
                        "state": vendor.state,
                        "pincode": vendor.pincode,
                        "latitude": float(vendor.latitude) if vendor.latitude else None,
                        "longitude": float(vendor.longitude) if vendor.longitude else None
                    }
        return None

    def get_user_details(self, obj):
        user = obj.order.user if obj.order else None
        if user:
            address = user.addresses.filter(is_primary=True).first()
            address_data = None
            if address:
                address_data = {
                    "address_line1": address.address_line1,
                    "address_line2": address.address_line2,
                    "city": address.city,
                    "state": address.state,
                    "country": address.country,
                    "pincode": address.pincode,
                    "latitude": float(address.latitude) if address.latitude else None,
                    "longitude": float(address.longitude) if address.longitude else None
                }
            
            return {
                "name": user.name,
                "mobile_number": user.mobile_number,
                "email": user.email,
                "address": address_data
            }
        return None

    def get_is_accepted(self, obj):
        return obj.status == 'ACCEPTED'

    def get_is_rejected(self, obj):
        return obj.status == 'REJECTED'


class DeliveryNotificationSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    vendor_name = serializers.SerializerMethodField()
    vendor_location = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_mobile = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_address = serializers.SerializerMethodField()
    delivery_charge = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNotification
        fields = [
            'id', 'message', 'created_at', 'is_read', 'order', 'order_id',
            'vendor_name', 'vendor_location',
            'user_name', 'user_mobile', 'user_email', 'user_address','delivery_charge'
        ]

    def get_vendor_name(self, obj):
        if obj.order and obj.order.checkout:
            items = obj.order.checkout.items.all()
            if items.exists():
                vendor = items.first().vendor
                return vendor.business_name if vendor else None
        return None
    
    def get_delivery_charge(self,obj):
        return obj.order.delivery_charge

    def get_vendor_location(self, obj):
        if obj.order and obj.order.checkout:
            items = obj.order.checkout.items.all()
            if items.exists():
                vendor = items.first().vendor
                if vendor:
                    return {
                        "address": vendor.address,
                        "landmark": vendor.business_landmark,
                        "city": vendor.city,
                        "state": vendor.state,
                        "pincode": vendor.pincode,
                        "latitude": vendor.latitude,
                        "longitude": vendor.longitude
                    }
        return None

    def get_user_name(self, obj):
        return obj.order.user.name if obj.order and obj.order.user else None

    def get_user_mobile(self, obj):
        return obj.order.user.mobile_number if obj.order and obj.order.user else None

    def get_user_email(self, obj):
        return obj.order.user.email if obj.order and obj.order.user else None

    def get_user_address(self, obj):
        user = obj.order.user if obj.order else None
        if user:
            address = user.addresses.filter(is_primary=True).first()
            if address:
                return {
                    "address_line1": address.address_line1,
                    "address_line2": address.address_line2,
                    "city": address.city,
                    "state": address.state,
                    "country": address.country,
                    "pincode": address.pincode,
                    "latitude":address.latitude,
                    "longitude":address.longitude
                }
        return None



class AcceptedOrderSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    user_details = serializers.SerializerMethodField()
    vendor_details = serializers.SerializerMethodField()
    assignment_status = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderAssign
        fields = [
            'id', 'order_id', 'assigned_at', 'status', 'is_accepted', 
            'is_rejected', 'user_details', 'vendor_details', 
            'assignment_status', 'delivery_charge'
        ]
    
    def get_assignment_status(self, obj):
        """Return human-readable assignment status"""
        if obj.is_accepted:
            return "Accepted"
        elif obj.is_rejected:
            return "Rejected"
        return "Pending"
    
    def get_user_details(self, obj):
        """Get user details with location name instead of lat/lon"""
        user = obj.order.user
        
        # Get address from checkout
        try:
            checkout = obj.order.checkout
            address = checkout.selected_address if hasattr(checkout, 'selected_address') else None
        except Exception:
            address = None
        
        address_data = None
        if address:
            # Get location name from lat/lon
            location_name = None
            if hasattr(address, 'latitude') and hasattr(address, 'longitude'):
                if address.latitude and address.longitude:
                    location_name = obj.get_location_name(address.latitude, address.longitude)
            
            address_data = {
                'address_line1': getattr(address, 'address_line1', ''),
                'address_line2': getattr(address, 'address_line2', ''),
                'city': getattr(address, 'city', ''),
                'state': getattr(address, 'state', ''),
                'country': getattr(address, 'country', ''),
                'pincode': getattr(address, 'pincode', ''),
                'location_name': location_name or f"{getattr(address, 'city', '')}, {getattr(address, 'state', '')}",
            }
        
        return {
            'name': user.get_full_name() or user.username,
            'email': user.email,
            'address': address_data
        }
    
    def get_vendor_details(self, obj):
        """Get vendor details with location name instead of lat/lon"""
        # Get vendor from first order item
        try:
            order_items = obj.order.order_items.all()
            if not order_items.exists():
                return None
            
            vendor = order_items.first().vendor
            
            # Get location name from lat/lon
            location_name = None
            if hasattr(vendor, 'latitude') and hasattr(vendor, 'longitude'):
                if vendor.latitude and vendor.longitude:
                    location_name = obj.get_location_name(vendor.latitude, vendor.longitude)
            
            return {
                'name': vendor.name,
                'address': getattr(vendor, 'address', ''),
                'landmark': getattr(vendor, 'landmark', ''),
                'city': getattr(vendor, 'city', ''),
                'state': getattr(vendor, 'state', ''),
                'pincode': getattr(vendor, 'pincode', ''),
                'location_name': location_name or f"{getattr(vendor, 'city', '')}, {getattr(vendor, 'state', '')}",
            }
        except Exception as e:
            print(f"Error getting vendor details: {e}")
            return None

class OrderAssignStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAssign
        fields = ['status']

from django.db import models

class DeliveryChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryCharges
        fields = [
            'id',
            'distance_from',
            'distance_to',
            'day_charge',
            'night_charge',
            'night_start_time',
            'night_end_time',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        distance_from = data.get('distance_from')
        distance_to = data.get('distance_to')
        
        # Check if distance_to is greater than distance_from
        if distance_to and distance_from and distance_to <= distance_from:
            raise serializers.ValidationError(
                "'distance_to' must be greater than 'distance_from'"
            )
        
        # Check for overlapping ranges
        instance_id = self.instance.id if self.instance else None
        
        # Query for overlapping ranges
        overlapping_charges = DeliveryCharges.objects.filter(
            models.Q(
                # Case 1: New range starts within existing range
                distance_from__lte=distance_from,
                distance_to__gt=distance_from
            ) | models.Q(
                # Case 2: New range ends within existing range
                distance_from__lt=distance_to,
                distance_to__gte=distance_to
            ) | models.Q(
                # Case 3: New range completely contains existing range
                distance_from__gte=distance_from,
                distance_to__lte=distance_to
            )
        )
        
        # Exclude the current instance when updating
        if instance_id:
            overlapping_charges = overlapping_charges.exclude(id=instance_id)
        
        if overlapping_charges.exists():
            overlapping = overlapping_charges.first()
            raise serializers.ValidationError({
                'distance_range': f'Distance range {distance_from}-{distance_to} km overlaps with existing range {overlapping.distance_from}-{overlapping.distance_to} km'
            })
        
        return data
    
    def validate_distance_from(self, value):
        if value < 0:
            raise serializers.ValidationError("Distance from must be non-negative")
        return value
    
    def validate_distance_to(self, value):
        if value <= 0:
            raise serializers.ValidationError("Distance to must be positive")
        return value
    
    def validate_day_charge(self, value):
        if value < 0:
            raise serializers.ValidationError("Day charge must be non-negative")
        return value
    
    def validate_night_charge(self, value):
        if value < 0:
            raise serializers.ValidationError("Night charge must be non-negative")
        return value