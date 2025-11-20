from django.db import models
from django.contrib.auth import get_user_model
from foodproduct.models import *
from groceryproducts.models import *
from fashion.models import *
from vendors.models import *
from decimal import Decimal


User = get_user_model()

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='cart_items')
    product_type = models.CharField(max_length=20, choices=[('clothing', 'Clothing'), ('dish', 'Dish'), ('grocery', 'Grocery')])
    product_id = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField(default=1)
    color = models.CharField(max_length=50, null=True, blank=True)
    size = models.CharField(max_length=10, null=True, blank=True)
    variant = models.CharField(max_length=50, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if self.product_type == 'clothing':
            product = Clothing.objects.get(id=self.product_id)
            if self.color and self.size:
                color_idx = next((i for i, c in enumerate(product.colors) if c['color_name'] == self.color), None)
                if color_idx is not None:
                    size_idx = next((i for i, s in enumerate(product.colors[color_idx]['sizes']) if s['size'] == self.size), None)
                    if size_idx is not None:
                        self.price = product.get_variant_offer_price(color_idx, size_idx)
        elif self.product_type == 'dish':
            product = Dish.objects.get(id=self.product_id)
            self.price = product.get_price_for_variant(self.variant) if self.variant else product.offer_price or product.price
        elif self.product_type == 'grocery':
            product = GroceryProducts.objects.get(id=self.product_id)
            self.price = product.get_price_for_weight(self.variant) if self.variant else product.offer_price or product.price

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_type} - {self.product_id} ({self.quantity})"


User = get_user_model()

class Checkout(models.Model):
    ORDER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("Picked", "Picked"),
        ("out for delivery", "Out for Delivery"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ('rejected', 'Rejected'),
        ("cancelled", "Cancelled"),
        ("return", "Return"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_id = models.CharField(max_length=50, unique=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True, unique=True)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Before discount
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')

    shipping_address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name="shipping_address", null=True, blank=True)
    contact_number = models.CharField(max_length=15,null=True,blank=True)

    coupon = models.ForeignKey('users.Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='checkouts_used')
    coupon_code = models.CharField(max_length=50, blank=True, null=True)  # Stored for backup or reporting
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_total(self):
        self.total_amount = sum(item.subtotal for item in self.items.all())
        self.final_amount = self.total_amount - self.coupon_discount
        self.save()

    def apply_coupon(self, coupon):
        """Applies a coupon and calculates discount."""
        if coupon:
            if coupon.discount_type == 'percentage':
                discount = (self.total_amount * coupon.discount_value) / 100
                if coupon.max_discount:
                    discount = min(discount, coupon.max_discount)
            else:
                discount = coupon.discount_value

            # Ensure minimum order amount is met
            if coupon.min_order_amount and self.total_amount < coupon.min_order_amount:
                return  # Do not apply

            self.coupon = coupon
            self.coupon_code = coupon.code
            self.coupon_discount = discount
            self.final_amount = self.total_amount - discount
            self.save()

    def __str__(self):
        return f"Order {self.order_id} - {self.user} - ₹{self.final_amount}"



class CheckoutItem(models.Model):
    checkout = models.ForeignKey(Checkout, on_delete=models.CASCADE, related_name='items')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='order_items')
    product_type = models.CharField(max_length=20, choices=[('clothing', 'Clothing'), ('dish', 'Dish'), ('grocery', 'Grocery')])
    product_id = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    color = models.CharField(max_length=50, null=True, blank=True)
    size = models.CharField(max_length=10, null=True, blank=True)
    variant = models.CharField(max_length=50, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)
        self.checkout.calculate_total()

    def __str__(self):
        return f"Order {self.checkout.order_id} - {self.product_type} ({self.quantity})"

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("out for delivery", "Out for Delivery"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ('rejected', 'Rejected'),
        ("cancelled", "Cancelled"),
        ("return", "Return"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    checkout = models.OneToOneField(Checkout, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=50, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_coupon = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_address = models.TextField()
    address = models.ForeignKey('users.Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    # billing_address = models.TextField()
    contact_number = models.CharField(max_length=15)
    delivery_pin = models.CharField(max_length=6, blank=True, null=True)
    product_details = models.JSONField(default=list, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reason = models.CharField(max_length=500,null=True,blank=True)
    description = models.TextField(null=True,blank=True)

    def __str__(self):
        return f"Order {self.order_id} - {self.user.username}"


    def get_active_items(self):
        return self.order_items.exclude(status='cancelled')

    def update_order_status(self):
        items = self.order_items.all()

        if not items.exists():
            return

        if items.filter(status='cancelled').count() == items.count():
            self.order_status = 'cancelled'
        elif items.filter(status='cancelled').exists():
            self.order_status = 'partial_cancelled'

        self.save()

    def recalculate_total(self):
        active_items = self.get_active_items()
        self.final_amount = sum(item.subtotal for item in active_items)

        if self.payment_status == 'paid' and self.order_items.filter(status='cancelled').exists():
            self.payment_status = 'partial_refunded'

        self.save()

class OrderItem(models.Model):
    ITEM_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("out for delivery", "Out for Delivery"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("return", "Return"),
    ]

    order = models.ForeignKey('Order', related_name='order_items', on_delete=models.CASCADE)
    product_id = models.IntegerField()  # Changed to IntegerField based on your data
    product_name = models.CharField(max_length=255)
    product_type = models.CharField(max_length=50)  # 'clothing', 'grocery', 'dish'
    quantity = models.PositiveIntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='pending')

    # Variant fields
    color = models.CharField(max_length=50, null=True, blank=True)
    size = models.CharField(max_length=50, null=True, blank=True)
    variant = models.CharField(max_length=100, null=True, blank=True)

    # Cancellation details
    cancel_reason = models.TextField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_orderitem'

    def __str__(self):
        return f"{self.product_name} - {self.status}"

NOTIFICATION_TYPES = [
    ('new_order', 'New Order'),
    ('order_cancelled', 'Order Cancelled'),
    ('payment_received', 'Payment Received'),
    ('refund_request', 'Refund Request'),
    ('stock_low', 'Low Stock Alert'),
    ('review_received', 'New Review'),
    ('general', 'General'),
]

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, null=True, blank=True)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='general')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

