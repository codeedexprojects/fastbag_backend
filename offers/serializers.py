from rest_framework import serializers
from .models import FoodOffer, FoodCoupon

class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodOffer
        fields = '__all__'

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCoupon
        fields = '__all__'
