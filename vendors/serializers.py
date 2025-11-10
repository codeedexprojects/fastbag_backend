from rest_framework import serializers
from .models import *
from datetime import datetime
from django.conf import settings
from foodproduct.models import *
from fashion.models import *
from groceryproducts.models import *

class StoreTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreType
        fields = ['id', 'name', 'description']


class VendorCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating and displaying vendor information"""

    # File fields with proper validation
    fssai_certificate = serializers.ImageField(
        required=False, 
        allow_null=True,
        max_length=None,
        use_url=True
    )
    store_logo = serializers.ImageField(
        required=True,
        max_length=None,
        use_url=True
    )
    display_image = serializers.ImageField(
        required=False, 
        allow_null=True,
        max_length=None,
        use_url=True
    )
    license = serializers.ImageField(
        required=True,
        max_length=None,
        use_url=True
    )
    id_proof = serializers.ImageField(
        required=False, 
        allow_null=True,
        max_length=None,
        use_url=True
    )
    passbook_image = serializers.ImageField(
        required=False, 
        allow_null=True,
        max_length=None,
        use_url=True
    )

    # Read-only fields
    store_type_name = serializers.CharField(source='store_type.name', read_only=True)
    
    # Coordinate fields with proper precision
    latitude = serializers.DecimalField(
        max_digits=12, 
        decimal_places=10, 
        required=False, 
        allow_null=True,
        coerce_to_string=False
    )
    longitude = serializers.DecimalField(
        max_digits=13, 
        decimal_places=10, 
        required=False, 
        allow_null=True,
        coerce_to_string=False
    )

    # URL fields for file access
    fssai_certificate_url = serializers.SerializerMethodField()
    store_logo_url = serializers.SerializerMethodField()
    display_image_url = serializers.SerializerMethodField()
    license_url = serializers.SerializerMethodField()
    id_proof_url = serializers.SerializerMethodField()
    passbook_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            'id', 'store_id', 'owner_name', 'email', 'business_name', 'business_location',
            'business_landmark', 'contact_number', 'address', 'city', 'state', 'pincode',
            'fssai_no', 'fssai_certificate', 'fssai_certificate_url',
            'store_logo', 'store_logo_url',
            'display_image', 'display_image_url',
            'license', 'license_url',
            'id_proof', 'id_proof_url',
            'passbook_image', 'passbook_image_url',
            'store_description',
            'store_type', 'store_type_name',
            'opening_time', 'closing_time',
            'is_approved', 'is_active', 'created_at',
            'is_restaurent', 'is_Grocery', 'is_fashion',
            'alternate_email', 'since',
            'longitude', 'latitude',
            'is_closed', 'commission'
        ]
        read_only_fields = ['id', 'store_id', 'created_at', 'is_approved']

    def get_file_url(self, file_field):
        """Helper method to get absolute URL for file fields"""
        request = self.context.get('request')
        if file_field and hasattr(file_field, 'url'):
            try:
                if request:
                    return request.build_absolute_uri(file_field.url)
                return file_field.url
            except Exception:
                return None
        return None

    def get_fssai_certificate_url(self, obj):
        return self.get_file_url(obj.fssai_certificate)

    def get_store_logo_url(self, obj):
        return self.get_file_url(obj.store_logo)

    def get_display_image_url(self, obj):
        return self.get_file_url(obj.display_image)

    def get_license_url(self, obj):
        return self.get_file_url(obj.license)

    def get_id_proof_url(self, obj):
        return self.get_file_url(obj.id_proof)

    def get_passbook_image_url(self, obj):
        return self.get_file_url(obj.passbook_image)
    
    def set_store_type_flags(self, instance, store_type):
        # Reset all first
        instance.is_restaurent = False
        instance.is_Grocery = False
        instance.is_fashion = False

        # Activate correct one based on store_type
        if store_type and store_type.name.lower() == "restaurent":
            instance.is_restaurent = True
        elif store_type and store_type.name.lower() == "grocery":
            instance.is_Grocery = True
        elif store_type and store_type.name.lower() == "fashion":
            instance.is_fashion = True


    def validate_email(self, value):
        """Validate email format"""
        if value and '@' not in value:
            raise serializers.ValidationError("Enter a valid email address.")
        return value

    def validate_alternate_email(self, value):
        """Validate alternate email format"""
        if value and '@' not in value:
            raise serializers.ValidationError("Enter a valid email address.")
        return value

    def validate_contact_number(self, value):
        """Validate contact number"""
        if value:
            # Remove common formatting characters
            cleaned = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not cleaned.isdigit():
                raise serializers.ValidationError("Contact number must contain only digits.")
            if len(cleaned) < 10:
                raise serializers.ValidationError("Contact number must be at least 10 digits.")
        return value

    def validate_latitude(self, value):
        """Validate latitude range"""
        if value is not None:
            if value < -90 or value > 90:
                raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        """Validate longitude range"""
        if value is not None:
            if value < -180 or value > 180:
                raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def validate_store_logo(self, value):
        """Validate store logo file"""
        if value:
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Store logo file size must be less than 5MB.")
            # Check file type
            if not value.content_type.startswith('image/'):
                raise serializers.ValidationError("Store logo must be an image file.")
        return value

    def validate_license(self, value):
        """Validate license file"""
        if value:
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("License file size must be less than 5MB.")
            # Check file type
            if not value.content_type.startswith('image/'):
                raise serializers.ValidationError("License must be an image file.")
        return value

    def validate(self, data):
        """Cross-field validation"""
        # Validate opening and closing times
        if 'opening_time' in data and 'closing_time' in data:
            if data['opening_time'] and data['closing_time']:
                if data['opening_time'] >= data['closing_time']:
                    raise serializers.ValidationError({
                        "closing_time": "Closing time must be after opening time."
                    })
        
        return data

    def create(self, validated_data):
        store_type = validated_data.get("store_type", None)

        vendor = Vendor.objects.create(**validated_data)

        # Set store type flags
        self.set_store_type_flags(vendor, store_type)
        vendor.save()

        return vendor


    def update(self, instance, validated_data):
        store_type = validated_data.get("store_type", instance.store_type)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        # Set store type flags
        self.set_store_type_flags(instance, store_type)
        instance.save()

        return instance




class VendorNameSerializer(serializers.ModelSerializer):
    opening_time = serializers.SerializerMethodField()
    closing_time = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = ['business_name', 'opening_time', 'closing_time','is_closed']

    def get_opening_time(self, obj):
        return obj.get_opening_time_str()

    def get_closing_time(self, obj):
        return obj.get_closing_time_str()

class VendorDetailSerializer(serializers.ModelSerializer):
    # Image fields - these will handle uploads
    fssai_certificate = serializers.ImageField(required=False)
    store_logo = serializers.ImageField(required=False)
    display_image = serializers.ImageField(required=False)
    license = serializers.ImageField(required=False)
    
    # SerializerMethodFields for read operations
    fssai_certificate_url = serializers.SerializerMethodField()
    store_logo_url = serializers.SerializerMethodField()
    display_image_url = serializers.SerializerMethodField()
    license_url = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    store_type_name = serializers.CharField(source='store_type.name', read_only=True)
    is_closed_now = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            'id', 'store_id', 'owner_name', 'email', 'business_name', 'business_location',
            'business_landmark', 'contact_number', 'address', 'city', 'state', 'pincode',
            'fssai_no', 'fssai_certificate', 'fssai_certificate_url', 'store_logo', 
            'store_logo_url', 'display_image', 'display_image_url', 'store_description',
            'store_type', 'store_type_name', 'opening_time', 'closing_time', 'license', 
            'license_url', 'is_approved', 'is_active', 'created_at', 'is_restaurent', 
            'is_Grocery', 'alternate_email', 'since', 'longitude', 'latitude', 'is_closed',
            'is_closed_now', 'is_favourite', 'id_proof', 'is_fashion', 'commission'
        ]
        read_only_fields = ['id', 'store_id', 'created_at', 'is_approved']

    def get_fssai_certificate_url(self, obj):
        if obj.fssai_certificate:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.fssai_certificate.url)
        return None

    def get_store_logo_url(self, obj):
        if obj.store_logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.store_logo.url)
        return None

    def get_display_image_url(self, obj):
        if obj.display_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.display_image.url)
        return None

    def get_license_url(self, obj):
        if obj.license:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.license.url)
        return None

    def get_is_favourite(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.is_authenticated:
            from users.models import CustomUser
            if isinstance(user, CustomUser):
                return FavoriteVendor.objects.filter(user=user, vendor=obj).exists()
        return False

    def get_is_closed_now(self, obj):
        return obj.is_closed_now if hasattr(obj, 'is_closed_now') else None

    def update(self, instance, validated_data):
        # Store updates in pending fields
        if 'contact_number' in validated_data:
            instance.pending_contact_number = validated_data.pop('contact_number')
        if 'fssai_certificate' in validated_data:
            instance.pending_fssai_certificate = validated_data.pop('fssai_certificate')
        if 'license' in validated_data:
            instance.pending_license = validated_data.pop('license')

        # Update other fields directly
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Mark the instance as pending approval
        instance.is_pending_update_approval = True
        instance.save()
        return instance

class VendorPendingDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Vendor
        fields = ['id','pending_fssai_certificate','pending_license','pending_contact_number']

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id','business_name','business_location','latitude','is_restaurent','is_Grocery','is_fashion','longitude','opening_time','display_image','is_closed','closing_time']

class VendorHomePageSerializer(serializers.ModelSerializer):
    is_favourite = serializers.SerializerMethodField()
    store_type = serializers.CharField(source='store_type.name',read_only=True)

    class Meta:
        model = Vendor
        fields = ['id', 'business_name', 'opening_time','closing_time','display_image', 'is_favourite','store_type','store_logo','business_location','is_closed']

    def get_is_favourite(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.is_authenticated:
            return FavoriteVendor.objects.filter(user=user, vendor=obj).exists()
        return False

class VendorLoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)


class VendorOTPVerifySerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)
    fcm_token = serializers.CharField(max_length=255,required=False)



class VendorApprovalStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'is_approved']

class CategorySerializer(serializers.ModelSerializer):
    StoreType_name = serializers.CharField(source='store_type.name',read_only=True)
    class Meta:
        model = Category
        fields = ['id','name','created_at','category_image','store_type','StoreType_name']


class ClothingSubCategorySerializerlist(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source = 'vendor.business_name',read_only=True)
    category_name = serializers.CharField(source = 'category.name',read_only=True)
    class Meta:
        model = ClothingSubCategory
        fields = ['id','vendor','vendor_name','category','category_name','name','enable_subcategory','subcategory_image',
                  'created_at']
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if instance.subcategory_image and request:
            representation['subcategory_image'] = request.build_absolute_uri(instance.subcategory_image.url)
        return representation

class GrocerySubCategorySerializerlist(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source = 'vendor.business_name',read_only=True)
    category_name = serializers.CharField(source = 'category.name',read_only=True)
    class Meta:
        model = GrocerySubCategories
        fields = ['id','vendor','vendor_name','category','category_name','name','enable_subcategory','subcategory_image',
                  'created_at']
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if instance.subcategory_image and request:
            representation['subcategory_image'] = request.build_absolute_uri(instance.subcategory_image.url)
        return representation

class FoodSubCategorySerializerlist(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source = 'vendor.business_name',read_only=True)
    category_name = serializers.CharField(source = 'category.name',read_only=True)
    class Meta:
        model = FoodSubCategories
        fields = ['id','vendor','vendor_name','category','category_name','name','enable_subcategory','subcategory_image',
                  'created_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if instance.subcategory_image and request:
            representation['subcategory_image'] = request.build_absolute_uri(instance.subcategory_image.url)
        return representation

class VendorfavSerializer(serializers.ModelSerializer):
    opening_time = serializers.SerializerMethodField()
    closing_time = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = ['business_name', 'opening_time','display_image', 'closing_time']

    def get_opening_time(self, obj):
        return obj.get_opening_time_str()

    def get_closing_time(self, obj):
        return obj.get_closing_time_str()


class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    store_type = serializers.CharField(source='category.store_type.name',read_only=True)

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'category', 'category_name','store_type', 'sub_category_image', 'is_active', 'created_at']

class SubCategoryRequestSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)

    class Meta:
        model = SubCategoryRequest
        fields = [
            'id', 'vendor', 'vendor_name', 'category', 'category_name', 'name',
            'sub_category_image', 'status', 'admin_remark', 'created_at'
        ]
        read_only_fields = ['status', 'admin_remark', 'created_at', 'vendor']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request.user, 'vendor'):
            validated_data['vendor'] = request.user.vendor
        return super().create(validated_data)


class AppCarouselSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.business_name',read_only=True)
    class Meta:
        model = AppCarousel
        fields = ['id','vendor','vendor_name','title','ads_image','created_at']


class AppCarouselSerializerByLoc(serializers.ModelSerializer):
    distance = serializers.SerializerMethodField()
    vendor_name = serializers.SerializerMethodField()

    class Meta:
        model = AppCarouselByLocation
        fields = ['id', 'vendor', 'vendor_name','title', 'ads_image', 'latitude', 'longitude', 'created_at', 'distance']

    def get_distance(self, obj):
        return getattr(obj, 'distance', None)
    
    def get_vendor_name(self, obj):
        return obj.vendor.owner_name


class VendorVideoSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.business_name", read_only=True)
    vendor_logo = serializers.SerializerMethodField()

    class Meta:
        model = VendorVideo
        fields = [
            "id", "vendor", "vendor_name", "title", "description",
            "video", "thumbnail", "is_active", "created_at", "vendor_logo"
        ]
        read_only_fields = ["id", "created_at", "vendor_name"]

    def get_vendor_logo(self, obj):
        request = self.context.get("request")
        if obj.vendor.store_logo and request:
            return request.build_absolute_uri(obj.vendor.store_logo.url)
        return None

class VendorcommissionSerializer(serializers.ModelSerializer):
    store_type= serializers.CharField(source='store_type.name',read_only=True)
    class Meta:
        model = Vendor
        fields = ['id','business_name','display_image','owner_name','business_location','contact_number','store_type']


class VendorCommissionSerializer(serializers.ModelSerializer):
    vendor = VendorcommissionSerializer(read_only=True)

    class Meta:
        model = VendorCommission
        fields = [
            "id",
            "vendor",
            "total_sales",
            "commission_percentage",
            "commission_amount",
            "payment_status",
            "created_at",
        ]

    def get_display_image(self, obj):
        request = self.context.get("request")
        if obj.display_image and request:
            return request.build_absolute_uri(obj.display_image.url)
        return None


class SubCategoryRequestSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    vendor_name = serializers.CharField(source="Vendor.business_name", read_only=True)


    class Meta:
        model = SubCategoryRequest
        fields = ["id", "category", "category_name", "name", "sub_category_image", "status", "created_at",'vendor','vendor_name']