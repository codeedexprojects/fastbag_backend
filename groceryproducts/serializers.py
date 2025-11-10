from rest_framework import serializers
from .models import *

class GroceryCategorySerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)  # Automatically use the URL for image field

    class Meta:
        model = Category
        fields = '__all__'


class GrocerySubCategorySerializer(serializers.ModelSerializer):
    vendor = serializers.PrimaryKeyRelatedField(read_only=True)  # Display vendor name
    category_name = serializers.CharField(source='category.name', read_only=True)  # Display category name
    store_type = serializers.CharField(source='vendor.store_type.name',read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name',read_only=True)

    class Meta:
        model = GrocerySubCategories
        fields = [
                    'id', 'vendor', 'category', 'category_name', 'name','store_type' ,
                    'subcategory_image', 'enable_subcategory', 'created_at','vendor_name'
                ]

    def validate_category(self, value):
        # Check if the category exists and is valid
        if not Category.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("This category does not exist.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        vendor_id = request.data.get('vendor_id')

        try:
            validated_data['vendor'] = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            raise serializers.ValidationError({"vendor": "The specified vendor does not exist."})

        return super().create(validated_data)


class GroceryProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroceryProductImage
        fields = ['id','image']

class GroceryProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    subcategory = serializers.PrimaryKeyRelatedField(queryset=SubCategory.objects.all())
    images = GroceryProductImageSerializer(many=True, required=False)
    category_name = serializers.SerializerMethodField()
    sub_category_name = serializers.SerializerMethodField()
    price_for_selected_weight = serializers.SerializerMethodField()
    offer_price = serializers.ReadOnlyField()
    discount = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    weights = serializers.JSONField(required=False)
    store_type = serializers.CharField(source='vendor.store_type.name', read_only=True)
    is_wishlisted = serializers.SerializerMethodField()
    vendor = serializers.PrimaryKeyRelatedField(queryset=Vendor.objects.all())

    class Meta:
        model = GroceryProducts
        fields = [
            'id', 'category', 'category_name', 'subcategory', 'vendor', 'sub_category_name', 'name', 'price',
            'offer_price', 'discount', 'description', 'weight_measurement',
            'price_for_selected_weight', 'is_offer_product', 'is_popular_product', 'weights',
            'is_available', 'created_at', 'images', 'store_type', 'is_wishlisted'
        ]

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_sub_category_name(self, obj):
        return obj.subcategory.name if obj.subcategory else None

    def get_price_for_selected_weight(self, obj):
        selected_weight = self.context.get('selected_weight')
        if selected_weight:
            try:
                return obj.get_price_for_weight(selected_weight)
            except (AttributeError, ValueError):
                pass
        return obj.price

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                from users.models import CustomUser
                if isinstance(request.user, CustomUser):
                    return Grocery_Wishlist.objects.filter(user=request.user, product=obj).exists()
            except (ValueError, TypeError, AttributeError):
                pass
        return False

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        product = GroceryProducts.objects.create(**validated_data)

        for image_data in images_data:
            GroceryProductImage.objects.create(product=product, **image_data)
        return product

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if images_data is not None:
            instance.images.all().delete()
            for image_data in images_data:
                GroceryProductImage.objects.create(product=instance, **image_data)
        return instance


class GroceryProductSerializerAdmin(serializers.ModelSerializer):
    vendor = serializers.PrimaryKeyRelatedField(
        queryset=Vendor.objects.all(),
        error_messages={'does_not_exist': 'Vendor not found.'}
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        error_messages={'does_not_exist': 'Category not found.'}
    )
    subcategory = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(),
        required=False,
        allow_null=True,
        error_messages={'does_not_exist': 'Subcategory not found.'}
    )

    # Other fields
    images = GroceryProductImageSerializer(many=True, required=False)
    category_name = serializers.SerializerMethodField()
    sub_category_name = serializers.SerializerMethodField()
    price_for_selected_weight = serializers.SerializerMethodField()
    offer_price = serializers.ReadOnlyField()
    discount = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    weights = serializers.JSONField()
    store_type = serializers.CharField(source='vendor.store_type.name', read_only=True)
    wholesale_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = GroceryProducts
        fields = [
            'id', 'vendor', 'category', 'category_name', 'subcategory', 'sub_category_name',
            'name', 'wholesale_price', 'price', 'offer_price', 'discount', 'description',
            'weight_measurement', 'price_for_selected_weight', 'is_offer_product',
            'is_popular_product', 'weights', 'is_available', 'created_at', 'images', 'store_type'
        ]

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_sub_category_name(self, obj):
        return obj.subcategory.name if obj.subcategory else None

    def get_price_for_selected_weight(self, obj):
        selected_weight = self.context.get('selected_weight')
        if selected_weight:
            return obj.get_price_for_weight(selected_weight)
        return obj.price

    def validate(self, data):

        vendor = data.get('vendor')
        if vendor and not Vendor.objects.filter(id=vendor.id).exists():
            raise serializers.ValidationError({"vendor": "Vendor not found."})

        category = data.get('category')
        if category and not Category.objects.filter(id=category.id).exists():
            raise serializers.ValidationError({"category": "Category not found."})

        subcategory = data.get('subcategory')
        if subcategory and not SubCategory.objects.filter(id=subcategory.id).exists():
            raise serializers.ValidationError({"subcategory": "Subcategory not found."})

        return data

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        product = GroceryProducts.objects.create(**validated_data)

        for image_data in images_data:
            GroceryProductImage.objects.create(product=product, **image_data)
        return product

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if images_data is not None:
            instance.images.all().delete()
            for image_data in images_data:
                GroceryProductImage.objects.create(product=instance, **image_data)
        return instance


class ProductSearchSerializer(serializers.Serializer):
    search_query = serializers.CharField(max_length=100, required=True)

class GroceryWishlistSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name',read_only=True)
    price = serializers.CharField(source='product.offer_price',read_only=True)
    description = serializers.CharField(source='product.description',read_only=True)
    product_details = GroceryProductSerializer(source='product',read_only=True)

    class Meta:
        model = Grocery_Wishlist
        fields = ['id', 'user', 'product', 'added_at','product_name','price','description','product_details']
        read_only_fields = ['id', 'added_at']

class GroceryProductReviewSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name',read_only=True)
    user_name = serializers.CharField(source='user.name',read_only=True)
    vendor = serializers.CharField(source='product.vendor.business_name',read_only=True)

    class Meta:
        model = GroceryProductReview
        fields = ['id', 'product','product_name', 'user','user_name','vendor', 'rating', 'review', 'created_at']
        read_only_fields = ['user', 'created_at']

class GroceryProductReportSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="grocery_product.name",read_only=True)
    user_name = serializers.CharField(source="user.name",read_only=True)
    vendor = serializers.CharField(source='product.vendor.business_name',read_only=True)

    class Meta:
        model = GroceryProductReport
        fields = ['id', 'grocery_product','product_name', 'user','user_name','vendor', 'reason', 'is_resolved', 'created_at']
        read_only_fields = ['is_resolved', 'created_at']

class GroceryCouponSerializer(serializers.ModelSerializer):
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
        model = GroceryCoupon
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

class GroceryCouponUsageSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    coupon = serializers.StringRelatedField()
    used_at = serializers.DateTimeField(format="%d/%m/%Y %H:%M:%S")

    class Meta:
        model = GroceryCouponUsage
        fields = ['user', 'coupon', 'used_at', 'is_valid']

class GroceryCouponUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroceryCoupon
        fields = ['id',
            'code', 'discount_type', 'discount_value',
            'valid_from', 'valid_to', 'is_active'
        ]
        read_only_fields = ['code']