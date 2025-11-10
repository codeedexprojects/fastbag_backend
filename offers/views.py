from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import FoodOffer, FoodCoupon
from .serializers import OfferSerializer, CouponSerializer
from django.utils.timezone import now
from rest_framework.permissions import IsAuthenticated
# Offer Views
class FoodOfferListView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self, request):
        offers = FoodOffer.objects.filter(is_active=True)
        serializer = OfferSerializer(offers, many=True)
        return Response(serializer.data)

class FoodOfferCreateView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self, request):
        serializer = OfferSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Coupon Views
class FoodCouponValidateView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self, request):
        coupon_code = request.data.get('coupon_code')
        cart_total = float(request.data.get('cart_total', 0))
        
        try:
            coupon = FoodCoupon.objects.get(code=coupon_code, is_active=True)
        except FoodCoupon.DoesNotExist:
            return Response({'error': 'Invalid or expired coupon'}, status=status.HTTP_400_BAD_REQUEST)

        # Check validity
        if now() < coupon.valid_from or now() > coupon.valid_till:
            return Response({'error': 'Coupon not valid at this time'}, status=status.HTTP_400_BAD_REQUEST)

        if cart_total < coupon.minimum_order_value:
            return Response({'error': f'Minimum order value is {coupon.minimum_order_value}'}, status=status.HTTP_400_BAD_REQUEST)

        if coupon.used_count >= coupon.usage_limit:
            return Response({'error': 'Coupon usage limit exceeded'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate discount
        if coupon.discount_type == 'PERCENTAGE':
            discount = (coupon.discount_value / 100) * cart_total
            if coupon.maximum_discount:
                discount = min(discount, coupon.maximum_discount)
        else:
            discount = coupon.discount_value

        discounted_total = cart_total - discount

        return Response({
            'success': True,
            'discount': discount,
            'discounted_total': discounted_total,
            'message': 'Coupon applied successfully!'
        })

class FoodCouponCreateView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self, request):
        serializer = CouponSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
