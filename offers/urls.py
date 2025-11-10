from django.urls import path
from .views import *

urlpatterns = [
    # Offers
    path('offers/', FoodOfferListView.as_view(), name='offer-list'),
    path('offers/create/', FoodOfferCreateView.as_view(), name='offer-create'),

    # Coupons
    path('coupons/validate/', FoodCouponValidateView.as_view(), name='coupon-validate'),
    path('coupons/create/', FoodCouponCreateView.as_view(), name='coupon-create'),
]
