from django.db import models
from vendors.models import Vendor
from django.utils import timezone
from django.utils.timezone import now
from users.models import CustomUser
from vendors.models import Category,SubCategory


class ClothingSubCategory(models.Model):
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='clothing_subcategories'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='clothing_subcategories'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    enable_subcategory = models.BooleanField(default=True)
    subcategory_image = models.ImageField(upload_to='clothing/subcategory')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Sub-category of {self.category.name} by {self.vendor.business_name})"


class Color(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='color_images/', blank=True, null=True)

    def __str__(self):
        return self.name

class Clothing(models.Model):

    GENDER_CHOICES = [
        ('M', 'Men'),
        ('W', 'Women'),
        ('U', 'Unisex'),
        ('K', 'Kids'),
    ]

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='clothing')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='clothing_items')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, related_name='clothing_items')
    name = models.CharField(max_length=150)
    description = models.TextField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    wholesale_price = models.DecimalField(default=0,max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base price for this item",null=True)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, help_text="Discount percentage", default=0)
    colors = models.JSONField(default=list,null=True)
    material = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    is_wishlisted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_offer_product = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.name} - {self.vendor.business_name}"

    def calculate_offer_price(self):
            if self.price and self.discount:
                return round(self.price * (1 - self.discount / 100), 2)
            return self.price

    @property
    def total_stock(self):
        total = 0
        for color in self.colors:
            for size in color.get('sizes', []):
                total += size.get('stock', 0)
        return total

    def save(self, *args, **kwargs):
        if self.colors is None:
            self.colors = []

        self.calculate_offer_price()

        for color in self.colors:
            for size in color.get('sizes', []):
                if 'price' not in size:
                    size['price'] = float(self.price)

        super().save(*args, **kwargs)


class ClothingColor(models.Model):
    clothing = models.ForeignKey("Clothing", on_delete=models.CASCADE, related_name="clothcolors")
    color_name = models.CharField(max_length=50)
    color_code = models.CharField(max_length=100,null=True)

    def __str__(self):
        return f"{self.color_name} - {self.clothing.name}"

class ClothingSize(models.Model):
    color = models.ForeignKey(ClothingColor, on_delete=models.CASCADE, related_name="sizes")
    size = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # New field
    stock = models.IntegerField()

    def save(self, *args, **kwargs):
        if self.offer_price and self.offer_price >= self.price:
            raise ValueError("Offer price must be lower than the original price.")
        super().save(*args, **kwargs)

    def reduce_stock(self, quantity):
        if self.stock < quantity:
            raise ValueError(f"Insufficient stock. Available: {self.stock}, Requested: {quantity}")
        self.stock -= quantity
        self.save()


    def __str__(self):
        return f"{self.color} - {self.size} - Price: {self.price} - Offer Price: {self.offer_price or 'N/A'}"


class ClothingImage(models.Model):
    clothing = models.ForeignKey(Clothing, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='clothing/images/')

    def __str__(self):
        return f"Image for {self.clothing.name}"

class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='coupons')
    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        """Check if the coupon is valid."""
        from django.utils.timezone import now
        return self.is_active and self.valid_from <= now() <= self.valid_to

    def __str__(self):
        return f"{self.code} ({self.vendor.business_name})"


class CouponUsage(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="coupon_usages")
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="coupon_usages")
    used_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'coupon')
    def __str__(self):
        return f"{self.user.mobile_number} used {self.coupon.code} on {self.used_at}"


class FashionWishlist(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='fashion_wishlist')
    cloth = models.ForeignKey(Clothing, on_delete=models.CASCADE, related_name='fashion_wishlists')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'cloth')

    def __str__(self):
        return f"{self.user} - {self.cloth.name}"

class FashionReview(models.Model):
    cloth = models.ForeignKey(Clothing, on_delete=models.CASCADE, related_name='fashion_reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='fashion_reviews')
    rating = models.DecimalField(max_digits=2, decimal_places=1, help_text="Rating from 1 to 5")
    review = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.name} for {self.cloth.name}"


class FashionReport(models.Model):
    cloth = models.ForeignKey(Clothing, on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cloth_reports')
    reason = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.cloth.name} by {self.user.username}"

