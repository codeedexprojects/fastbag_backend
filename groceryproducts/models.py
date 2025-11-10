from django.db import models
from vendors.models import Vendor
from users.models import *
from django.utils.timezone import now
from vendors.models import Category,SubCategory

# Create your models here.

class GrocerySubCategories(models.Model):
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='grocery_subcategories'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='grocery_subcategories'
    )
    name = models.CharField(max_length=100, default='sample')
    subcategory_image = models.ImageField(upload_to='grocery/subcategory_images/', null=True, blank=True)
    enable_subcategory = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.name} (Sub-category of {self.category.name} by {self.vendor.business_name})"


class GroceryProducts(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='grocery')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='grocery', null=True, blank=True)
    name = models.CharField(max_length=100)
    wholesale_price = models.DecimalField(default=0,max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Discount percentage")
    description = models.TextField(default="product")
    weight_measurement = models.CharField(max_length=100)
    is_available = models.BooleanField(default=True)
    is_offer_product = models.BooleanField(default=False)
    is_popular_product = models.BooleanField(default=False)
    weights = models.JSONField(default=list,help_text="Store different weights with their respective prices, quantities, and stock status as a dictionary")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    is_wishlisted = models.BooleanField(default=False)


    def calculate_offer_price(self):
        """
        Automatically calculate the offer price based on the discount percentage.
        """
        if self.discount and self.price:
            discount_amount = (self.discount / 100) * self.price
            self.offer_price = self.price - discount_amount
        else:
            self.offer_price = self.price


    def get_price_for_weight(self, weight):
        """
        Get the price for a specific weight from the stored weights data.
        This method handles both dictionaries and lists in the weights field.
        """
        if isinstance(self.weights, dict):
            # Handle weights as a dictionary
            weight_data = self.weights.get(weight, {})
            return weight_data.get('price', self.price)

        elif isinstance(self.weights, list):
            # Handle weights as a list of dictionaries
            for weight_data in self.weights:
                if weight_data.get('weight') == weight:
                    return weight_data.get('price', self.price)
        return self.price  # Default to the base price if weight not found

    def get_quantity_for_weight(self, weight):
        """
        Get the quantity for a specific weight from the stored weights data.
        Handles both dictionary and list formats.
        """
        if isinstance(self.weights, dict):
            # Handle weights as a dictionary
            weight_data = self.weights.get(weight, {})
            return weight_data.get('quantity', 0)

        elif isinstance(self.weights, list):
            # Handle weights as a list of dictionaries
            for weight_data in self.weights:
                if weight_data.get('weight') == weight:
                    return weight_data.get('quantity', 0)
        return 0  # Default to 0 if weight not found

    def get_stock_status_for_weight(self, weight):
        """
        Get the stock status for a specific weight from the stored weights data.
        Handles both dictionary and list formats.
        """
        if isinstance(self.weights, dict):
            # Handle weights as a dictionary
            weight_data = self.weights.get(weight, {})
            return weight_data.get('is_in_stock', False)

        elif isinstance(self.weights, list):
            # Handle weights as a list of dictionaries
            for weight_data in self.weights:
                if weight_data.get('weight') == weight:
                    return weight_data.get('is_in_stock', False)
        return False  # Default to False if weight not found

    def save(self, *args, **kwargs):
        self.calculate_offer_price()  # Make sure this is called before saving
        super(GroceryProducts, self).save(*args, **kwargs)
    def reduce_stock(self, variant, quantity):
        if isinstance(self.weights, list):
            for weight in self.weights:
                if weight['weight'] == variant:
                    if weight['quantity'] < quantity:
                        return False
                    weight['quantity'] -= quantity
                    weight['is_in_stock'] = weight['quantity'] > 0
                    return True
        elif isinstance(self.weights, dict):
            if self.weights.get(variant, {}).get('quantity', 0) < quantity:
                return False
            self.weights[variant]['quantity'] -= quantity
            self.weights[variant]['is_in_stock'] = self.weights[variant]['quantity'] > 0
            return True
        return False

    def __str__(self):
        return self.name


class GroceryProductImage(models.Model):
    product = models.ForeignKey(GroceryProducts, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/images/', null=True, blank=True)
    def __str__(self):
        return f"Image for {self.product.name}"

class Grocery_Wishlist(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='grocery')
    product = models.ForeignKey(GroceryProducts, on_delete=models.CASCADE, related_name='grocery')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user} - {self.product.name}"

class GroceryProductReview(models.Model):
    product = models.ForeignKey(
        GroceryProducts, on_delete=models.CASCADE, related_name='reviews'
    )
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='product_reviews'
    )
    rating = models.DecimalField(
        max_digits=2, decimal_places=1, help_text="Rating from 1 to 5"
    )
    review = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.name} for {self.product.name}"

class GroceryProductReport(models.Model):
    grocery_product = models.ForeignKey(GroceryProducts, on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='groceryproduct_reports')
    reason = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.grocery_product.name} by {self.user.username}"

class GroceryCoupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='grocerycoupons')
    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        return self.is_active and self.valid_from <= now() <= self.valid_to

    def __str__(self):
        return self.code

class GroceryCouponUsage(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="Grocerycoupon_usages")
    coupon = models.ForeignKey(GroceryCoupon, on_delete=models.CASCADE, related_name="Grocerycoupon_usages")
    used_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'coupon')
    def __str__(self):
        return f"{self.user.mobile_number} used {self.coupon.code} on {self.used_at}"