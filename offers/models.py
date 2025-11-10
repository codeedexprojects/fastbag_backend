from django.db import models
from django.utils.timezone import now
from foodproduct.models import Dish,FoodSubCategories
from vendors.models import Category


class FoodOffer(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)  
    start_date = models.DateTimeField(default=now)
    end_date = models.DateTimeField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    sub_category = models.ForeignKey(FoodSubCategories, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Dish, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()

    def __str__(self):
        return self.title

class FoodCoupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('PERCENTAGE', 'Percentage'),
        ('FIXED_AMOUNT', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=15, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)  
    minimum_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField(default=now)
    valid_till = models.DateTimeField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    sub_category = models.ForeignKey(FoodSubCategories, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Dish, on_delete=models.SET_NULL, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()


    def __str__(self):
        return self.code
