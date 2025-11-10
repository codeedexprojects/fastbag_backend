from rest_framework import serializers
from fashion.models import *
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from vendors.serializers import CategorySerializer
import decimal
from django.conf import settings
from django.utils.functional import lazy

class ClothingImageSerializer(ModelSerializer):
    image_url = SerializerMethodField()

    class Meta:
        model = ClothingImage
        fields = ['id', 'image', 'image_url', 'clothing']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

class ClothingCategorySerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.business_name', read_only=True)
    class Meta:
        model = Category
        fields = ['id','store','store_name', 'name', 'description', 'is_active','category_image', 'created_at', 'updated_at']

class ClothingSubCategorySerializer(serializers.ModelSerializer):
    vendor = serializers.PrimaryKeyRelatedField(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    store_type = serializers.CharField(source='vendor.store_type.name',read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name',read_only=True)

    class Meta:
        model = SubCategory
        fields = [
                    'id', 'vendor', 'category', 'category_name', 'name','store_type' ,
                    'subcategory_image', 'enable_subcategory', 'created_at','vendor_name'
                ]

    def validate_category(self, value):
        if not Category.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("This category does not exist.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        vendor_id = request.data.get('vendor_id')
        if not vendor_id:
            raise serializers.ValidationError({"vendor": "Vendor ID must be provided."})

        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            raise serializers.ValidationError({"vendor": "The specified vendor does not exist."})
        validated_data['vendor'] = vendor
        return super().create(validated_data)




class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name', 'image']

class ClothingImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ClothingImage
        fields = ['id', 'image_url', 'clothing', 'image']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and obj.image.url:  # Check if the image exists
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class ClothingSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClothingSize
        fields = ['size', 'price', 'offer_price', 'stock']

class ClothingColorSerializer(serializers.ModelSerializer):
    sizes = ClothingSizeSerializer(many=True)  # Nest sizes inside color

    class Meta:
        model = ClothingColor
        fields = ['color_name', 'color_code', 'sizes']



class ClothingSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True, source='category'
    )
    subcategory = serializers.StringRelatedField(read_only=True)
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), write_only=True, source='subcategory', required=False
    )

    images = ClothingImageSerializer(many=True, read_only=True)
    image_files = serializers.ListField(
        child=serializers.ImageField(max_length=None, use_url=False),
        write_only=True,
        required=False
    )

    colors = ClothingColorSerializer(many=True, required=False)

    total_stock = serializers.IntegerField(read_only=True)
    offer_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    categoryid = serializers.PrimaryKeyRelatedField(source='category', read_only=True)
    subcategoryid = serializers.PrimaryKeyRelatedField(source='subcategory', read_only=True)
    store_type = serializers.CharField(source='vendor.store_type.name', read_only=True)
    is_wishlisted = serializers.SerializerMethodField()
    vendor = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Clothing
        fields = [
            'id', 'vendor', 'category', 'category_id', 'subcategory', 'subcategory_id',
            'name', 'description', 'gender', 'price', 'discount', 'offer_price','wholesale_price',
            'total_stock', 'colors', 'material', 'images', 'image_files', 'is_active','subcategoryid','categoryid',
            'created_at', 'updated_at','store_type','is_offer_product','is_wishlisted'
        ]
        read_only_fields = ['total_stock', 'offer_price']

    def validate_colors(self, value):
        if not value:
            return value
        for color in value:
            if 'color_name' not in color:
                raise serializers.ValidationError("Each color entry must contain 'color_name'.")
            for size in color.get('sizes', []):
                if not all(k in size for k in ['size', 'price', 'stock']):
                    raise serializers.ValidationError("Each size entry must contain 'size', 'price', and 'stock'.")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Make sure colors are serialized properly
        data['colors'] = ClothingColorSerializer(instance.clothcolors.all(), many=True).data
        return data

    def create(self, validated_data):
        image_files = validated_data.pop('image_files', [])
        colors_data = validated_data.pop('colors', [])

        clothing = Clothing.objects.create(**validated_data)

        for color_data in colors_data:
            sizes_data = color_data.pop('sizes', [])
            color_instance = ClothingColor.objects.create(clothing=clothing, **color_data)

            for size_data in sizes_data:
                ClothingSize.objects.create(color=color_instance, **size_data)

        for image_file in image_files:
            ClothingImage.objects.create(clothing=clothing, image=image_file)

        return clothing

    def update(self, instance, validated_data):
        image_files = validated_data.pop('image_files', [])
        colors_data = validated_data.pop('colors', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if colors_data is not None:
            instance.clothcolors.all().delete()
            for color_data in colors_data:
                sizes_data = color_data.pop('sizes', [])
                color_instance = ClothingColor.objects.create(clothing=instance, **color_data)

                for size_data in sizes_data:
                    ClothingSize.objects.create(color=color_instance, **size_data)

        instance.save()

        for image_file in image_files:
            ClothingImage.objects.create(clothing=instance, image=image_file)

        return instance

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                from users.models import CustomUser
                if isinstance(request.user, CustomUser):
                    return FashionWishlist.objects.filter(user=request.user, cloth=obj).exists()
            except (ValueError, TypeError, AttributeError):
                pass
        return False
    
    
class ClothingSerializeruser(serializers.ModelSerializer):
    category = serializers.StringRelatedField(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True, source='category'
    )
    subcategory = serializers.StringRelatedField(read_only=True)
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), write_only=True, source='subcategory', required=False
    )

    images = ClothingImageSerializer(many=True, read_only=True)
    image_files = serializers.ListField(
        child=serializers.ImageField(max_length=None, use_url=False),
        write_only=True,
        required=False
    )

    colors = ClothingColorSerializer(many=True)

    total_stock = serializers.IntegerField(read_only=True)
    offer_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    categoryid = serializers.PrimaryKeyRelatedField(source='category', read_only=True)
    subcategoryid = serializers.PrimaryKeyRelatedField(source='subcategory', read_only=True)
    store_type = serializers.CharField(source='vendor.store_type.name',read_only=True)
    is_wishlisted = serializers.SerializerMethodField()

    class Meta:
        model = Clothing
        fields = [
            'id', 'vendor', 'category', 'category_id', 'subcategory', 'subcategory_id',
            'name', 'description', 'gender', 'price', 'discount', 'offer_price','wholesale_price',
            'total_stock', 'colors', 'material', 'images', 'image_files', 'is_active','subcategoryid','categoryid',
            'created_at', 'updated_at','store_type','is_wishlisted'
        ]
        read_only_fields = ['total_stock', 'offer_price']

    def validate_colors(self, value):
        for color in value:
            if 'color_name' not in color:
                raise serializers.ValidationError("Each color entry must contain 'color_name'.")
            for size in color.get('sizes', []):
                if not all(k in size for k in ['size', 'price', 'stock']):
                    raise serializers.ValidationError("Each size entry must contain 'size', 'price', and 'stock'.")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['colors'] = ClothingColorSerializer(instance.clothcolors.all(), many=True).data  # Ensure correct related name
        return data

    def create(self, validated_data):
        image_files = validated_data.pop('image_files', [])
        colors_data = validated_data.pop('colors', [])

        # Create clothing instance
        clothing = Clothing.objects.create(**validated_data)

        # Create ClothingColor instances
        for color_data in colors_data:
            sizes_data = color_data.pop('sizes', [])
            color_instance = ClothingColor.objects.create(clothing=clothing, **color_data)

            # Create related ClothingSize instances
            for size_data in sizes_data:
                ClothingSize.objects.create(color=color_instance, **size_data)

        # Create associated images
        for image_file in image_files:
            ClothingImage.objects.create(clothing=clothing, image=image_file)

        return clothing



    def update(self, instance, validated_data):
        image_files = validated_data.pop('image_files', [])
        colors_data = validated_data.pop('colors', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if colors_data is not None:
            instance.clothcolors.all().delete()  # Delete old colors
            for color_data in colors_data:
                sizes_data = color_data.pop('sizes', [])
                color_instance = ClothingColor.objects.create(clothing=instance, **color_data)

                for size_data in sizes_data:
                    ClothingSize.objects.create(color=color_instance, **size_data)

        instance.save()

        for image_file in image_files:
            ClothingImage.objects.create(clothing=instance, image=image_file)

        return instance

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return FashionWishlist.objects.filter(user=request.user, cloth=obj).exists()
        return False


class CouponSerializer(serializers.ModelSerializer):
    valid_from = serializers.DateTimeField(
        format="%d/%m/%Y",
        input_formats=["%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]
    )
    valid_to = serializers.DateTimeField(
        format="%d/%m/%Y",
        input_formats=["%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]
    )
    vendor_name = serializers.CharField(source='vendor.business_name',read_only=True)
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'vendor','vendor_name','discount_type', 'discount_value',
            'valid_from', 'valid_to', 'is_active','is_admin'
        ]

    def validate(self, data):
        if data['valid_from'] >= data['valid_to']:
            raise serializers.ValidationError("Valid from date must be before valid to date.")
        if data['discount_value'] <= 0:
            raise serializers.ValidationError("Discount value must be positive.")
        return data

class CouponUsageSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    coupon = serializers.StringRelatedField()
    used_at = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")

    class Meta:
        model = CouponUsage
        fields = ['user', 'coupon', 'used_at', 'is_valid']

class CouponUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            'code', 'discount_type', 'discount_value',
            'valid_from', 'valid_to', 'is_active'
        ]
        read_only_fields = ['code']

class FashionWishlistSerializer(serializers.ModelSerializer):
    cloth_name = serializers.ReadOnlyField(source='cloth.name')
    cloth_price = serializers.ReadOnlyField(source='cloth.price')
    user_name = serializers.CharField(source='user.name',read_only=True)
    cloth_details = ClothingSerializeruser(source='cloth', read_only=True)  # Nested ClothingSerializer

    class Meta:
        model = FashionWishlist
        fields = ['id', 'user', 'user_name','cloth', 'cloth_name', 'cloth_price', 'added_at','cloth_details']
        read_only_fields = ['user', 'added_at']

class FashionReviewSerializer(serializers.ModelSerializer):
    cloth_name = serializers.ReadOnlyField(source='cloth.name')
    user_name = serializers.ReadOnlyField(source='user.name')
    vendor = serializers.ReadOnlyField(source='cloth.vendor.business_name')

    class Meta:
        model = FashionReview
        fields = ['id', 'cloth', 'cloth_name', 'user', 'user_name','vendor', 'rating', 'review', 'created_at']
        read_only_fields = ['user', 'created_at']

class FashionReportSerializer(serializers.ModelSerializer):
    cloth_name = serializers.ReadOnlyField(source='cloth.name')
    user_name = serializers.ReadOnlyField(source='user.username')
    vendor = serializers.ReadOnlyField(source='cloth.vendor.business_name')
    class Meta:
        model = FashionReport
        fields = ['id', 'cloth', 'cloth_name', 'user', 'user_name', 'vendor','reason', 'is_resolved', 'created_at']
        read_only_fields = ['user', 'is_resolved', 'created_at']