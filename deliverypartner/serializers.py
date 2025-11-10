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
            'place'
        ]

    def validate_mobile_number(self, value):
        # Add any custom validation for mobile number here
        if len(value) < 10:
            raise serializers.ValidationError("Mobile number must be at least 10 digits.")
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
    order_id = serializers.CharField(source='order.order_id')
    delivery_boy_name = serializers.CharField(source='accepted_by.name', read_only=True)
    delivery_boy_number = serializers.IntegerField(source='accepted_by.mobile_number',read_only=True)
    vendor_details = serializers.SerializerMethodField()
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = OrderAssign
        fields = [
            'id', 'order_id', 'delivery_boy_name','delivery_boy_number', 'status', 'assigned_at',
            'vendor_details', 'user_details','is_accepted','is_rejected'
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
                        "latitude": vendor.latitude,
                        "longitude": vendor.longitude
                    }
        return None

    def get_user_details(self, obj):
        user = obj.order.user if obj.order else None
        if user:
            primary_address = user.addresses.filter(is_primary=True).first()
            return {
                "name": user.name,
                "mobile_number": user.mobile_number,
                "email": user.email,
                "address": {
                    "address_line1": primary_address.address_line1 if primary_address else None,
                    "address_line2": primary_address.address_line2 if primary_address else None,
                    "city": primary_address.city if primary_address else None,
                    "state": primary_address.state if primary_address else None,
                    "country": primary_address.country if primary_address else None,
                    "pincode": primary_address.pincode if primary_address else None,
                    "latitude":primary_address.latitude if primary_address else None,
                    "longitude":primary_address.longitude if primary_address else None
                }
            }
        return None

class OrderAssignStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAssign
        fields = ['status']


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
        
        if distance_to and distance_from and distance_to <= distance_from:
            raise serializers.ValidationError(
                "'distance_to' must be greater than 'distance_from'"
            )
        
        return data
    
    def validate_day_charge(self, value):
        if value < 0:
            raise serializers.ValidationError("Day charge must be positive")
        return value
    
    def validate_night_charge(self, value):
        if value < 0:
            raise serializers.ValidationError("Night charge must be positive")
        return value