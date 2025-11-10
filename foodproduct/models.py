from django.db import models
from users.models import *
from vendors.models import Vendor
from django.utils.timezone import now
from django.utils import timezone
from vendors.models import Category,SubCategory


class FoodSubCategories(models.Model):
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='food_subcategories'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='food_subcategories'
    )
    name = models.CharField(max_length=100, default='sample')
    subcategory_image = models.ImageField(upload_to='food/subcategory_images/', null=True, blank=True)
    enable_subcategory = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.name} (Sub-category of {self.category.name} by {self.vendor.business_name})"

class Dish(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='dishes')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='dishes')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='dishes', null=True, blank=True)
    name = models.CharField(max_length=255)
    wholesale_price = models.DecimalField(default=0,max_digits=10, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, help_text="Discount percentage", default=0)
    variants = models.JSONField(default=list,help_text="Store different variants (name, price, stock status) as a dictionary")
    is_available = models.BooleanField(default=True)
    is_veg = models.BooleanField(default=False)
    is_offer_product = models.BooleanField(default=False)
    is_popular_product = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_wishlisted = models.BooleanField(default=False)


    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Override the save method to automatically calculate the offer price
        based on the discount percentage.
        """
        self.calculate_offer_price()
        super().save(*args, **kwargs)

    def calculate_offer_price(self):
        """
        Automatically calculate the offer price based on the discount percentage.
        """
        if self.discount and self.price:
            discount_amount = (self.discount / 100) * self.price
            self.offer_price = self.price - discount_amount
        else:
            self.offer_price = self.price

    def apply_coupon(self, coupon, user):
        """
        Apply a coupon to the product for a specific user.
        """
        if not coupon.is_active:
            raise ValueError("Coupon is not active.")

        now = timezone.now()
        if not (coupon.valid_from <= now <= coupon.valid_to):
            raise ValueError("Coupon is not valid at this time.")

        # Check if the coupon has already been used
        usage, created = FoodCouponUsage.objects.get_or_create(user=user, coupon=coupon)
        if not created and not usage.is_valid:
            raise ValueError("Coupon has already been used by this user.")

        # Mark the coupon as used if it's valid
        usage.is_valid = False
        usage.save()

        # Calculate the discount
        if coupon.discount_type == 'percentage':
            discount_amount = (coupon.discount_value / 100) * self.price
        else:
            discount_amount = coupon.discount_value

        return max(self.price - discount_amount, 0)

    def get_price_for_variant(self, variant_name):
        try:
            # Ensure variants is a list
            if isinstance(self.variants, list):
                for variant in self.variants:
                    if variant.get("name", "").lower() == variant_name.lower():
                        return float(variant.get("price", self.price))
            return float(self.price)
        except Exception:
            return float(self.price)


class DishImage(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='dish_images/')

    def __str__(self):
        return f"Image for {self.dish.name}"

class DishAddOn(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='addons')
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, help_text="Discount percentage", default=0)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_popular_product = models.BooleanField(default=False)
    is_offer_product = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class DishAddonImage(models.Model):
    dish_addon = models.ForeignKey(DishAddOn, on_delete=models.CASCADE, related_name='addon_images')
    image = models.ImageField(upload_to='dish_addon_images/')

    def __str__(self):
        return f"Image for {self.dish.name}"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Override the save method to automatically calculate the offer price
        based on the discount percentage.
        """
        self.calculate_offer_price()
        super().save(*args, **kwargs)


    def calculate_offer_price(self):
        """
        Automatically calculate the offer price based on the discount percentage.
        """
        if self.discount and self.price:
            discount_amount = (self.discount / 100) * self.price
            self.offer_price = self.price - discount_amount
        else:
            self.offer_price = self.price

class Wishlist(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wishlist')
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='wishlists')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'dish')

    def __str__(self):
        return f"{self.user} - {self.dish.name}"

class DishReview(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='dish_reviews')
    rating = models.DecimalField(max_digits=2, decimal_places=1, help_text="Rating from 1 to 5")
    review = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.name} for {self.dish.name}"


class DishReport(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='dish_reports')
    reason = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.dish.name} by {self.user.username}"

class VendorBannerFoodProducts(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='food_banners')
    product = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='highlighted_in_banners')
    banner_image = models.ImageField(upload_to='banners/', help_text="Upload the banner image")
    description = models.TextField(null=True, blank=True, help_text="Short description of the offer")
    is_active = models.BooleanField(default=True, help_text="Only active banners will be displayed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Banner for {self.product.name} by {self.vendor.name}"

class FoodCoupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='foodcoupons')
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

class FoodCouponUsage(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="Foodcoupon_usages")
    coupon = models.ForeignKey(FoodCoupon, on_delete=models.CASCADE, related_name="Foodcoupon_usages")
    used_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'coupon')
    def __str__(self):
        return f"{self.user.mobile_number} used {self.coupon.code} on {self.used_at}"