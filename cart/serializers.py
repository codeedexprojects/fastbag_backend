from rest_framework import serializers
from .models import Cart, CartItem
from fashion.models import Clothing, ClothingImage
from foodproduct.models import Dish, DishImage
from groceryproducts.models import GroceryProducts, GroceryProductImage
from .models import Checkout, CheckoutItem
from cart.models import Cart, CartItem , Order , OrderItem , Notification
import uuid
import razorpay
from django.conf import settings
from decimal import Decimal
from django.utils.timezone import now
from users.models import Coupon
from groceryproducts.models import GroceryCoupon
from foodproduct.models import FoodCoupon
from vendors.models import Vendor
from django.utils import timezone
from django.conf import settings
from urllib.parse import urljoin
from users.models import UserLocation
from deliverypartner.models import DeliveryBoy
from deliverypartner.models import DeliveryNotification

class CartItemSerializer(serializers.ModelSerializer):
    product_details = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    selected_variant_details = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "cart", "vendor", "product_type", "product_id", "quantity", "variant", "price", "product_details", "total_amount", "selected_variant_details"]

    def get_product_details(self, obj):
        product_model = {
            "Fashion": Clothing,
            "Restaurant": Dish,
            "Grocery": GroceryProducts
        }.get(obj.product_type)

        product = product_model.objects.filter(id=obj.product_id).first() if product_model else None

        return {
            "name": product.name if product else "Unknown",
            "images": [self.context['request'].build_absolute_uri(img.image.url) for img in product.images.all()] if product and hasattr(product, "images") else [],
            "description": product.description if hasattr(product, "description") else "No description available"
        }

    def get_total_amount(self, obj):
        return obj.quantity * float(obj.price)

    def get_selected_variant_details(self, obj):
        product_model = {
            "Fashion": Clothing,
            "Restaurent": Dish,
            "Fashion": GroceryProducts
        }.get(obj.product_type)

        product = product_model.objects.filter(id=obj.product_id).first() if product_model else None

        if product:
            if obj.product_type == "Grocery":
                return {"selected_weight": obj.variant, "price_for_weight": product.get_price_for_weight(obj.variant)}
            elif obj.product_type == "Fashion":
                return {"selected_size": obj.variant, "price_for_size": product.get_price_for_size(obj.variant)}
            elif obj.product_type == "Restaurant":
                variant_details = next((v for v in product.variants if v["name"] == obj.variant), None)
                return variant_details if variant_details else {"selected_variant": obj.variant}

        return {"selected_variant": obj.variant}

    def get_selected_variant_details(self, obj):
        product_model = {
            "Fashion": Clothing,
            "Restaurent": Dish,
            "Grocery": GroceryProducts
        }.get(obj.product_type)

        product = product_model.objects.filter(id=obj.product_id).first() if product_model else None

        if product:
            if obj.product_type == "Grocery":
                return {"selected_weight": obj.variant, "price_for_weight": product.get_price_for_weight(obj.variant)}

            elif obj.product_type == "Fashion":
                # Extract color and size from the variant field
                variant_data = obj.variant.split(",")  # Assuming variant is stored as "Color,Size"
                color_name = variant_data[0].strip() if len(variant_data) > 0 else None
                size_name = variant_data[1].strip() if len(variant_data) > 1 else None

                # Find the matching color object
                selected_color = next((color for color in product.colors if color["color_name"] == color_name), None)
                if selected_color:
                    # Find the matching size object
                    selected_size = next((size for size in selected_color["sizes"] if size["size"] == size_name), None)
                    if selected_size:
                        return {
                            "selected_color": color_name,
                            "selected_size": size_name,
                            "price_for_size": selected_size["price"]
                        }

            elif obj.product_type == "Restaurant":
                variant_details = next((v for v in product.variants if v["name"] == obj.variant), None)
                return variant_details if variant_details else {"selected_variant": obj.variant}

        return {"selected_variant": obj.variant}



class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'created_at', 'items']


class CheckoutItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    product_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CheckoutItem
        fields = '__all__'
    
    def get_product_name(self, obj):
        """Get product name based on product type - ONLY check the correct table"""
        # Make sure we're checking the product_type field from CheckoutItem
        product_type = getattr(obj, 'product_type', '').lower()
        
        try:
            if product_type == 'grocery':
                product = GroceryProducts.objects.get(id=obj.product_id)
                return product.name
            
            elif product_type == 'restaurant':
                product = Dish.objects.get(id=obj.product_id)
                return product.name
            
            elif product_type == 'fashion' or not product_type:
                # Default to clothing for backward compatibility
                product = Clothing.objects.get(id=obj.product_id)
                return product.name
            
            else:
                return f"Unknown Product Type: {product_type}"
                
        except (Clothing.DoesNotExist, GroceryProducts.DoesNotExist, Dish.DoesNotExist):
            return f"Product {obj.product_id} (Not Found)"
    
    def get_product_image(self, obj):
        """Get product image based on product type - ONLY check the correct table"""
        request = self.context.get('request')
        product_type = getattr(obj, 'product_type', '').lower()
        
        try:
            if product_type == 'grocery':
                product = GroceryProducts.objects.get(id=obj.product_id)
                if hasattr(product, 'image') and product.image and request:
                    return request.build_absolute_uri(product.image.url)
            
            elif product_type == 'restaurant':
                product = Dish.objects.get(id=obj.product_id)
                if hasattr(product, 'image') and product.image and request:
                    return request.build_absolute_uri(product.image.url)
            
            elif product_type == 'fashion' or not product_type:
                product = Clothing.objects.get(id=obj.product_id)
                if hasattr(product, 'images'):
                    first_image = product.images.first()
                    if first_image and first_image.image and request:
                        return request.build_absolute_uri(first_image.image.url)
        
        except (Clothing.DoesNotExist, GroceryProducts.DoesNotExist, Dish.DoesNotExist):
            pass
        
        return ""
    
    def get_product_type_display(self, obj):
        """Return user-friendly product type"""
        product_type = getattr(obj, 'product_type', '').lower()
        
        if product_type == 'grocery':
            return 'Grocery'
        elif product_type == 'restaurant':
            return 'Restaurant'
        elif product_type == 'fashion':
            return 'Fashion'
        else:
            return 'Fashion'
        
import logging

logger = logging.getLogger(__name__)


class CheckoutSerializer(serializers.ModelSerializer):
    """
    Serializer for checkout process.
    Validates cart, coupon, and creates checkout with proper calculations.
    """
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    contact_number = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Checkout
        fields = [
            'user', 'payment_method', 'shipping_address',
            'contact_number', 'coupon_code', 'order_id', 'total_amount',
            'final_amount', 'coupon_discount', 'discount_amount'
        ]
        read_only_fields = ['order_id', 'total_amount', 'final_amount', 'coupon_discount', 'discount_amount']

    def validate_payment_method(self, value):
        """Validate payment method."""
        valid_methods = ['online', 'cod', 'card', 'upi']
        if value not in valid_methods:
            raise serializers.ValidationError(
                f"Invalid payment method. Must be one of: {', '.join(valid_methods)}"
            )
        return value

    def validate_contact_number(self, value):
        """Validate contact number format."""
        if value:
            # Remove spaces and special characters
            cleaned = ''.join(filter(str.isdigit, value))
            if len(cleaned) < 10 or len(cleaned) > 15:
                raise serializers.ValidationError(
                    "Contact number must be between 10 and 15 digits."
                )
        return value

    def validate(self, data):
        """
        Comprehensive validation for checkout data.
        Validates cart, calculates totals, and applies coupon if provided.
        """
        user = self.context['request'].user

        # Fetch cart items
        cart_items = CartItem.objects.filter(cart__user=user).select_related('vendor')

        if not cart_items.exists():
            raise serializers.ValidationError({"cart": "Your cart is empty."})

        # Calculate total amount
        total_amount = Decimal('0.00')
        for item in cart_items:
            item_total = Decimal(str(item.price)) * item.quantity
            total_amount += item_total

        logger.info(f"Total cart amount for user {user.id}: {total_amount}")

        # Initialize discount
        discount_amount = Decimal('0.00')
        coupon_code = data.get('coupon_code')

        # Validate and apply coupon if provided
        if coupon_code:
            coupon_result = self._validate_and_apply_coupon(
                coupon_code, total_amount, user
            )
            discount_amount = coupon_result['discount_amount']
            data['coupon_code'] = coupon_result['coupon_code']
            logger.info(f"Coupon applied: {coupon_code}, Discount: {discount_amount}")
        else:
            data['coupon_code'] = None

        # Calculate final amount
        final_amount = total_amount - discount_amount

        # Ensure final amount is not negative
        if final_amount < 0:
            final_amount = Decimal('0.00')

        # Set calculated values
        data['total_amount'] = total_amount
        data['discount_amount'] = discount_amount  # For the model field
        data['coupon_discount'] = discount_amount
        data['final_amount'] = final_amount

        logger.info(
            f"Checkout validation complete - Total: {total_amount}, "
            f"Discount: {discount_amount}, Final: {final_amount}"
        )

        return data

    def _validate_and_apply_coupon(self, coupon_code, total_amount, user):
        """
        Validate coupon code and calculate discount.
        Returns dict with coupon_code and discount_amount.
        """
        now = timezone.now()

        try:
            # Fetch active coupon within valid date range
            coupon = Coupon.objects.filter(
                code=coupon_code,
                valid_from__lte=now,
                valid_to__gte=now,
                is_active=True  # Assuming there's an is_active field
            ).first()

            if not coupon:
                raise serializers.ValidationError({
                    "coupon_code": "Invalid or expired coupon code."
                })

            # Check minimum order amount requirement
            if hasattr(coupon, 'min_order_amount') and coupon.min_order_amount:
                min_amount = Decimal(str(coupon.min_order_amount))
                if total_amount < min_amount:
                    raise serializers.ValidationError({
                        "coupon_code": f"Minimum order amount of ₹{min_amount} required for this coupon."
                    })

            # Check usage limit per user (if applicable)
            if hasattr(coupon, 'usage_limit_per_user') and coupon.usage_limit_per_user:
                usage_count = Checkout.objects.filter(
                    user=user,
                    coupon_code=coupon_code
                ).count()
                
                if usage_count >= coupon.usage_limit_per_user:
                    raise serializers.ValidationError({
                        "coupon_code": "You have already used this coupon the maximum number of times."
                    })

            # Check total usage limit (if applicable)
            if hasattr(coupon, 'total_usage_limit') and coupon.total_usage_limit:
                total_usage = Checkout.objects.filter(coupon_code=coupon_code).count()
                
                if total_usage >= coupon.total_usage_limit:
                    raise serializers.ValidationError({
                        "coupon_code": "This coupon has reached its usage limit."
                    })

            # Calculate discount amount
            discount_amount = Decimal('0.00')

            if coupon.discount_type == 'percentage':
                discount_value = Decimal(str(coupon.discount_value))
                discount_amount = (total_amount * discount_value) / Decimal('100')
                
                # Apply maximum discount cap if exists
                if hasattr(coupon, 'max_discount') and coupon.max_discount:
                    max_discount = Decimal(str(coupon.max_discount))
                    discount_amount = min(discount_amount, max_discount)

            elif coupon.discount_type == 'fixed':
                discount_amount = Decimal(str(coupon.discount_value))

            else:
                raise serializers.ValidationError({
                    "coupon_code": "Invalid coupon discount type."
                })

            # Ensure discount doesn't exceed total amount
            discount_amount = min(discount_amount, total_amount)

            return {
                "coupon_code": coupon.code,
                "discount_amount": discount_amount
            }

        except Coupon.DoesNotExist:
            raise serializers.ValidationError({
                "coupon_code": "Invalid coupon code."
            })

    def create(self, validated_data):
        """
        Create checkout instance with calculated amounts.
        Note: This method may not be used if the view handles creation directly.
        """
        user = self.context['request'].user

        # Generate unique order ID
        order_id = str(uuid.uuid4())

        # Create Checkout instance
        checkout = Checkout.objects.create(
            user=user,
            order_id=order_id,
            total_amount=validated_data['total_amount'],
            final_amount=validated_data['final_amount'],
            discount_amount=validated_data.get('discount_amount', Decimal('0.00')),
            payment_method=validated_data.get('payment_method'),
            shipping_address=validated_data.get('shipping_address'),
            contact_number=validated_data.get('contact_number', ''),
            coupon_code=validated_data.get('coupon_code'),
            coupon_discount=validated_data['coupon_discount'],
            payment_status='pending'
        )

        logger.info(f"Checkout created: Order ID {checkout.order_id}, User {user.id}")

        return checkout

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product_id',
            'product_name',
            'product_type',
            'quantity',
            'price_per_unit',
            'subtotal',
            'status',
            'variant',
            'cancel_reason',
            'cancelled_at',
        ]
        read_only_fields = ['id', 'cancelled_at']

class OrderSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    product_details = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'order_id',
            'user',
            'user_name',
            'total_amount',
            'payment_method',
            'payment_status',
            'order_status',
            'shipping_address',
            'contact_number',
            'created_at',
            'updated_at',
            'final_amount',
            'used_coupon',
            'product_details',
            'delivery_pin',
        ]

    def get_product_details(self, obj):
        ordered_items = []
        request = self.context.get('request')

        product_details = obj.product_details or []
        
        # Separate product IDs by type
        clothing_ids = []
        grocery_ids = []
        dish_ids = []
        
        for item in product_details:
            product_id = item.get('product_id')
            product_type = item.get('product_type', '').lower()
            
            if product_id:
                if product_type == 'grocery':
                    grocery_ids.append(product_id)
                elif product_type == 'restaurant':
                    dish_ids.append(product_id)
                else:
                    # Default to clothing if no type specified or type is 'fashion'
                    # This handles old orders without product_type
                    clothing_ids.append(product_id)
        
        # Bulk fetch from each product type separately
        clothings = {c.id: c for c in Clothing.objects.filter(id__in=clothing_ids).prefetch_related('images')}
        groceries = {g.id: g for g in GroceryProducts.objects.filter(id__in=grocery_ids)}
        dishes = {d.id: d for d in Dish.objects.filter(id__in=dish_ids)}

        for item in product_details:
            # Convert product_id to integer for lookup
            product_id_str = str(item.get('product_id'))
            try:
                product_id_int = int(item.get('product_id'))
            except (ValueError, TypeError):
                product_id_int = None

            quantity = item.get('quantity', 0) or 0
            
            # Determine product type from item data
            stored_product_type = item.get('product_type', '').lower()
            
            # Look up product based on stored product_type
            product = None
            product_source = None
            
            if product_id_int:
                if stored_product_type == 'grocery':
                    product = groceries.get(product_id_int)
                    product_source = 'grocery'
                elif stored_product_type == 'restaurant':
                    product = dishes.get(product_id_int)
                    product_source = 'dish'
                else:
                    # Default to clothing for backwards compatibility
                    product = clothings.get(product_id_int)
                    product_source = 'clothing'
                    
                # If product not found in expected type, try other types (for old orders)
                if not product:
                    if product_id_int in clothings:
                        product = clothings[product_id_int]
                        product_source = 'clothing'
                    elif product_id_int in groceries:
                        product = groceries[product_id_int]
                        product_source = 'grocery'
                    elif product_id_int in dishes:
                        product = dishes[product_id_int]
                        product_source = 'dish'
            
            product_name = getattr(product, 'name', '') or item.get('product_name', f'Product {product_id_str}')

            # Initialize product_info with all necessary fields
            product_info = {
                "id": item.get('id'),
                "product_id": product_id_str,
                "product_name": product_name,
                "product_type": None,
                "quantity": quantity,
                "price_per_unit": item.get('price_per_unit', 0),
                "subtotal": item.get('subtotal', 0),
                "status": item.get('status'),
                "variant": item.get('variant'),
                "cancel_reason": item.get('cancel_reason'),
                "cancelled_at": item.get('cancelled_at'),
                "product_image": "",
                "images": [],
                "selected_color": None,
                "selected_size": None,
                "available_colors": [],
                "selected_weight": None,
                "selected_variant": None,
                "available_variants": [],
            }

            if product:
                # Fallbacks for missing data
                if not product_info['product_name']:
                    product_info['product_name'] = getattr(product, 'name', '')

                if not product_info['price_per_unit']:
                    product_info['price_per_unit'] = getattr(product, 'price', 0)

                if not product_info['subtotal']:
                    product_info['subtotal'] = quantity * product_info['price_per_unit']

                # Product-specific attribute handling based on actual product source
                if product_source == 'clothing':
                    product_info['product_type'] = 'Fashion'
                    product_info['available_colors'] = product.colors or []

                    # Handling images for Clothing
                    image_urls = []
                    if hasattr(product, 'images') and request:
                        images = product.images.all()
                        image_urls = [request.build_absolute_uri(img.image.url) for img in images if img.image]

                    product_info['images'] = image_urls
                    product_info['product_image'] = image_urls[0] if image_urls else ''

                    variant = item.get('variant')
                    if variant and '-' in variant:
                        color_part, size_part = variant.split('-', 1)
                        product_info['selected_color'] = color_part.strip()
                        product_info['selected_size'] = size_part.strip()
                    else:
                        product_info['selected_color'] = item.get('color')
                        product_info['selected_size'] = item.get('size')

                    # Cleanup irrelevant fields
                    product_info.pop('selected_weight', None)
                    product_info.pop('selected_variant', None)
                    product_info.pop('available_variants', None)

                elif product_source == 'grocery':
                    product_info['product_type'] = 'Grocery'
                    
                    # Handle grocery images if your GroceryProducts model has images
                    # For now, leaving empty or you can add default grocery image
                    if hasattr(product, 'image') and product.image and request:
                        product_info['product_image'] = request.build_absolute_uri(product.image.url)
                        product_info['images'] = [product_info['product_image']]
                    else:
                        product_info['images'] = []
                        product_info['product_image'] = ''

                    weight = item.get('weight') or item.get('selected_weight')
                    if not weight:
                        variant = item.get('variant')
                        if variant:
                            weight = variant.strip()
                    product_info['selected_weight'] = weight

                    # Cleanup irrelevant fields
                    product_info.pop('selected_color', None)
                    product_info.pop('selected_size', None)
                    product_info.pop('available_colors', None)
                    product_info.pop('selected_variant', None)
                    product_info.pop('available_variants', None)

                elif product_source == 'dish':
                    product_info['product_type'] = 'Restaurant'
                    
                    # Handle dish images if your Dish model has images
                    if hasattr(product, 'image') and product.image and request:
                        product_info['product_image'] = request.build_absolute_uri(product.image.url)
                        product_info['images'] = [product_info['product_image']]
                    else:
                        product_info['images'] = []
                        product_info['product_image'] = ''

                    product_info['available_variants'] = product.variants or []
                    product_info['selected_variant'] = item.get('variant') or item.get('selected_variant')

                    # Cleanup irrelevant fields
                    product_info.pop('selected_color', None)
                    product_info.pop('selected_size', None)
                    product_info.pop('available_colors', None)
                    product_info.pop('selected_weight', None)

            else:
                # If product not found, try to preserve stored product_type from order
                if stored_product_type:
                    if stored_product_type == 'grocery':
                        product_info['product_type'] = 'Grocery'
                    elif stored_product_type == 'restaurant':
                        product_info['product_type'] = 'Restaurant'
                    else:
                        product_info['product_type'] = 'Fashion'
                
                product_info['error'] = 'Product not found'

            ordered_items.append(product_info)

        return ordered_items



class CartCheckoutItemSerializer(serializers.ModelSerializer):
    product_details = serializers.SerializerMethodField()

    class Meta:
        model = CheckoutItem
        fields = ['product_id', 'product_type', 'quantity', 'color', 'size', 'variant', 'price', 'subtotal', 'product_details']

    def get_product_details(self, obj):
        """Fetch product details dynamically based on product type"""
        if obj.product_type == 'clothing':
            product = Clothing.objects.filter(id=obj.product_id).first()
        elif obj.product_type == 'dish':
            product = Dish.objects.filter(id=obj.product_id).first()
        elif obj.product_type == 'grocery':
            product = GroceryProducts.objects.filter(id=obj.product_id).first()
        else:
            return None

        if product:
            return {
                "name": product.name,
                "image": product.image.url if product.image else None,
                "description": product.description,
                "price": obj.price,
            }
        return None


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'created_at', 'order', 'user']
        read_only_fields = ['id', 'created_at', 'order', 'user']


class DeliveryBoySerializer(serializers.ModelSerializer):
    """Serializer for delivery boy details"""
    class Meta:
        model = DeliveryBoy
        fields = [
            'id',
            'name',
            'phone_number',
            'email',
            'vehicle_type',
            'vehicle_number',
            'is_available',
            'current_latitude',
            'current_longitude',
            'profile_image',
        ]


class VendorBasicSerializer(serializers.ModelSerializer):
    """Serializer for vendor details in order"""
    opening_time_str = serializers.CharField(source='get_opening_time_str', read_only=True)
    closing_time_str = serializers.CharField(source='get_closing_time_str', read_only=True)
    
    class Meta:
        model = Vendor
        fields = [
            'id',
            'store_id',
            'business_name',
            'owner_name',
            'email',
            'contact_number',
            'address',
            'city',
            'state',
            'pincode',
            'store_logo',
            'display_image',
            'business_location',
            'business_landmark',
            'opening_time_str',
            'closing_time_str',
            'latitude',
            'longitude',
            'is_closed',
        ]


class UserLocationSerializer(serializers.ModelSerializer):
    """Serializer for user location"""
    class Meta:
        model = UserLocation
        fields = ['latitude', 'longitude']
class OrderDetailSerializer(serializers.ModelSerializer):
    """Enhanced order serializer with vendor, delivery boy, and location details"""
    # User details from the relationship
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_mobile_number = serializers.CharField(source='user.mobile_number', read_only=True)
    
    product_details = serializers.SerializerMethodField()
    vendor_details = serializers.SerializerMethodField()
    delivery_boy = serializers.SerializerMethodField()
    user_location = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'order_id',
            'user',
            'user_name',
            'user_email',
            'user_mobile_number',
            'total_amount',
            'payment_method',
            'payment_status',
            'order_status',
            'shipping_address',
            'contact_number',
            'created_at',
            'updated_at',
            'final_amount',
            'used_coupon',
            'product_details',
            'delivery_pin',
            'vendor_details',
            'delivery_boy',
            'user_location',
        ]

    def get_product_details(self, obj):
        """Get product details - reusing existing logic from OrderSerializerAdmin"""
        ordered_items = []
        request = self.context.get('request')

        product_details = obj.product_details or []
        product_ids = [item.get('product_id') for item in product_details if item.get('product_id')]

        from fashion.models import Clothing
        from groceryproducts.models import GroceryProducts
        from foodproduct.models import Dish
        
        clothings = {str(c.id): c for c in Clothing.objects.filter(id__in=product_ids).prefetch_related('images')}
        groceries = {str(g.id): g for g in GroceryProducts.objects.filter(id__in=product_ids)}
        dishes = {str(d.id): d for d in Dish.objects.filter(id__in=product_ids)}

        for item in product_details:
            product_id = str(item.get('product_id'))
            quantity = item.get('quantity', 0) or 0
            product = clothings.get(product_id) or groceries.get(product_id) or dishes.get(product_id)
            product_name = getattr(product, 'name', '') or item.get('product_name', f'Product {product_id}')

            product_info = {
                "id": item.get('id'),
                "product_id": product_id,
                "product_name": product_name,
                "product_type": None,
                "quantity": quantity,
                "price_per_unit": item.get('price_per_unit', 0),
                "subtotal": item.get('subtotal', 0),
                "status": item.get('status'),
                "variant": item.get('variant'),
                "cancel_reason": item.get('cancel_reason'),
                "cancelled_at": item.get('cancelled_at'),
                "product_image": "",
                "images": [],
                "vendor_id": None,
                "vendor_name": None,
            }

            if product:
                if not product_info['product_name']:
                    product_info['product_name'] = getattr(product, 'name', '')

                if not product_info['price_per_unit']:
                    product_info['price_per_unit'] = getattr(product, 'price', 0)

                if not product_info['subtotal']:
                    product_info['subtotal'] = quantity * product_info['price_per_unit']

                image_urls = []
                if hasattr(product, 'images'):
                    images = product.images.all()
                    image_urls = [request.build_absolute_uri(img.image.url) for img in images if img.image]

                product_info['images'] = image_urls
                product_info['product_image'] = image_urls[0] if image_urls else ''

                # Add vendor info
                if hasattr(product, 'vendor'):
                    product_info['vendor_id'] = product.vendor.id
                    product_info['vendor_name'] = product.vendor.business_name

                if isinstance(product, Clothing):
                    product_info['product_type'] = 'clothing'
                elif isinstance(product, GroceryProducts):
                    product_info['product_type'] = 'grocery'
                elif isinstance(product, Dish):
                    product_info['product_type'] = 'dish'
            else:
                product_info['error'] = 'Product not found'

            ordered_items.append(product_info)

        return ordered_items

    def get_vendor_details(self, obj):
        """Get vendor details from order products"""
        product_details = obj.product_details or []
        if not product_details:
            return []

        product_ids = [item.get('product_id') for item in product_details if item.get('product_id')]
        
        from fashion.models import Clothing
        from groceryproducts.models import GroceryProducts
        from foodproduct.models import Dish
        
        vendor_ids = set()
        
        # Get vendor IDs from products
        for clothing in Clothing.objects.filter(id__in=product_ids).select_related('vendor'):
            if clothing.vendor:
                vendor_ids.add(clothing.vendor.id)
        
        for grocery in GroceryProducts.objects.filter(id__in=product_ids).select_related('vendor'):
            if grocery.vendor:
                vendor_ids.add(grocery.vendor.id)
            
        for dish in Dish.objects.filter(id__in=product_ids).select_related('vendor'):
            if dish.vendor:
                vendor_ids.add(dish.vendor.id)

        # Get vendor details
        from vendors.models import Vendor
        vendors = Vendor.objects.filter(id__in=vendor_ids)
        return VendorBasicSerializer(vendors, many=True, context=self.context).data

    def get_delivery_boy(self, obj):
        """Get assigned delivery boy details"""
        try:
            from deliverypartner.models import DeliveryNotification
            # Get the latest delivery notification for this order
            notification = DeliveryNotification.objects.filter(
                order=obj
            ).select_related('delivery_boy').order_by('-created_at').first()
            
            if notification and notification.delivery_boy:
                from .serializers import DeliveryBoySerializer
                return DeliveryBoySerializer(notification.delivery_boy).data
            return None
        except Exception as e:
            return None

    def get_user_location(self, obj):
        """Get user location if available"""
        try:
            from users.models import UserLocation
            # Get the latest user location
            user_location = UserLocation.objects.filter(
                user=obj.user
            ).order_by('-id').first()
            
            if user_location:
                return UserLocationSerializer(user_location).data
            
            return None
        except Exception as e:
            return None