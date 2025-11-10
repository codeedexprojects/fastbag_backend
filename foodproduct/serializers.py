from rest_framework import serializers
from .models import *

class FoodCategorySerializer(serializers.ModelSerializer):
    # store_name = serializers.CharField(source='store.business_name', read_only=True)

    class Meta:
        model = Category
        fields = '__all__'


class FoodSubCategorySerializer(serializers.ModelSerializer):
    vendor = serializers.PrimaryKeyRelatedField(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)  # Display category name
    store_type = serializers.CharField(source='vendor.store_type.name',read_only=True)

    class Meta:
        model = FoodSubCategories
        fields = [
                'id', 'vendor', 'category', 'category_name', 'name','store_type' ,
                'subcategory_image', 'enable_subcategory', 'created_at','vendor_name'
            ]

    def validate_category(self, value):
        # Check if the category exists
        if not Category.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("This category does not exist.")
        return value

    def create(self, validated_data):
        # Assign the authenticated user (vendor) directly
        validated_data['vendor'] = self.context['request'].user
        return super().create(validated_data)


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'business_name', 'store_logo']

class DishImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishImage
        fields = ['id', 'image']

class DishCreateSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    image_files = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    images = serializers.SerializerMethodField()
    store_type = serializers.CharField(source='vendor.store_type.name', read_only=True)
    is_wishlisted = serializers.SerializerMethodField()
    vendor = serializers.PrimaryKeyRelatedField(queryset=Vendor.objects.all())

    class Meta:
        model = Dish
        fields = ['id', 'vendor', 'vendor_name', 'category', 'category_name',
                  'subcategory', 'subcategory_name', 'name', 'description', 'price',
                  'wholesale_price', 'offer_price', 'variants', 'discount',
                  'is_available', 'images', 'image_files', 'is_popular_product',
                  'is_offer_product', 'store_type','is_veg','is_wishlisted']

    def create(self, validated_data):
        image_files = validated_data.pop('image_files', [])
        dish = Dish.objects.create(**validated_data)
        for image in image_files:
            DishImage.objects.create(dish=dish, image=image)
        return dish

    def update(self, instance, validated_data):
        image_files = validated_data.pop('image_files', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if image_files:
            instance.images.all().delete()
            for image in image_files:
                DishImage.objects.create(dish=instance, image=image)

        return instance

    def get_images(self, obj):
        request = self.context.get('request')
        try:
            return DishImageSerializer(obj.images.all(), many=True, context={'request': request}).data
        except AttributeError:
            return []

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                from users.models import CustomUser
                if isinstance(request.user, CustomUser):
                    return Wishlist.objects.filter(user=request.user, dish=obj).exists()
            except (ValueError, TypeError, AttributeError):
                pass
        return False


class Dishlistserializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.business_name',read_only=True)
    category_name = serializers.CharField(source='category.name',read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name',read_only=True)
    image_urls = DishImageSerializer(source='images', many=True, read_only=True)

    class Meta:
        model = Dish
        fields = ['id','vendor','vendor_name','category','category_name','subcategory','subcategory_name', 'name', 'description', 'price',
                  'offer_price', 'discount', 'is_available', 'images', 'image_urls', 'is_popular_product',
                  'is_offer_product', 'is_available','is_veg','is_wishlisted']


class ProductSearchSerializer(serializers.Serializer):
    search_query = serializers.CharField(max_length=100, required=True)


class FoodCategorySerializerlist(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class VendorCategorySerializer(serializers.ModelSerializer):
    categories = FoodCategorySerializerlist(many=True, read_only=True, source='foodcategory_set')

    class Meta:
        model = Vendor
        fields = ['id', 'business_name', 'store_id', 'categories']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'category_image', 'food_subcategories']

class FoodSubCategorySerializer(serializers.ModelSerializer):
    category = serializers.IntegerField(source='category.id',read_only=True)
    category_name = serializers.CharField(source='category.name',read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name',read_only=True)
    store_type = serializers.CharField(source='vendor.store_type.name',read_only=True)

    class Meta:
        model = FoodSubCategories
        fields = ['id', 'name', 'subcategory_image','category', 'category_name','enable_subcategory','vendor','vendor_name','store_type','created_at']

class FoodSubCategorycreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodSubCategories
        fields = ['id', 'name', 'subcategory_image','category', 'enable_subcategory','vendor']

class DishAddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishAddonImage
        fields = ['id', 'image']

class DishAddOnSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True
    )
    image_urls = DishAddonSerializer(source='images', many=True, read_only=True)
    class Meta:
        model = DishAddOn
        fields = ['id', 'name', 'price','description','offer_price','discount','images', 'image_urls','is_offer_product','is_popular_product','is_available','created_at']

class WishlistSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='dish.name', read_only=True)
    price = serializers.CharField(source='dish.offer_price', read_only=True)
    description = serializers.CharField(source='dish.description', read_only=True)
    Wishlisted = serializers.SerializerMethodField()
    dish_detail = DishCreateSerializer(source='dish',read_only=True)

    class Meta:
        model = Wishlist
        fields = [
            'id',
            'user',
            'dish',
            'added_at',
            'product_name',
            'price',
            'description',
            'Wishlisted',
            'dish_detail'
        ]
        read_only_fields = ['id', 'added_at']

    def get_Wishlisted(self, obj):
        return True


class DishReviewSerializer(serializers.ModelSerializer):
    dish_name = serializers.CharField(source='dish.name',read_only=True)
    user_name = serializers.CharField(source='user.name',read_only=True)
    vendor = serializers.CharField(source='dish.vendor.business_name',read_only=True)

    class Meta:
        model = DishReview
        fields = ['id', 'dish', 'dish_name', 'user','user_name','vendor','rating', 'review', 'created_at']
        read_only_fields = ['id','user' ,'created_at']

class DishReportSerializer(serializers.ModelSerializer):
    dishname = serializers.CharField(source="dish.name",read_only=True)
    user_name = serializers.CharField(source="user.name",read_only=True)
    vendor = serializers.CharField(source='dish.vendor.business_name',read_only=True)

    class Meta:
        model = DishReport
        fields = ['id', 'dish','dishname', 'user','user_name', 'vendor','reason', 'is_resolved', 'created_at']
        read_only_fields = ['is_resolved', 'created_at']


class VendorBannerFoodProductsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name',read_only=True)
    class Meta:
        model = VendorBannerFoodProducts
        fields = ['id', 'vendor', 'product','product_name', 'banner_image', 'description', 'is_active', 'created_at', 'updated_at']

class FoodCouponSerializer(serializers.ModelSerializer):
    valid_from = serializers.DateTimeField(
        format="%d/%m/%Y",
        input_formats=["%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]
    )
    valid_to = serializers.DateTimeField(
        format="%d/%m/%Y",
        input_formats=["%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]
    )
    vendor_name=serializers.CharField(source='vendor.business_name',read_only=True)
    class Meta:
        model = FoodCoupon
        fields = [
            'id', 'code', 'discount_type', 'discount_value',
            'valid_from', 'valid_to', 'is_active','vendor','vendor_name'
        ]

    def validate(self, data):
        if data['valid_from'] >= data['valid_to']:
            raise serializers.ValidationError("Valid from date must be before valid to date.")
        if data['discount_value'] <= 0:
            raise serializers.ValidationError("Discount value must be positive.")
        return data

class FoodCouponUsageSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    coupon = serializers.StringRelatedField()
    used_at = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")

    class Meta:
        model = FoodCouponUsage
        fields = ['user', 'coupon', 'used_at', 'is_valid']

class FoodCouponUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCoupon
        fields = [
            'code', 'discount_type', 'discount_value',
            'valid_from', 'valid_to', 'is_active'
        ]
        read_only_fields = ['code']