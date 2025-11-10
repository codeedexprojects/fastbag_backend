from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny,IsAuthenticated
from users.models import Coupon
from users.serializers import CouponSerializer,CouponSerializeruser
from vendors.models import Vendor
from rest_framework.views import APIView
from rest_framework.response import Response
from vendors.authentication import VendorJWTAuthentication
from django.utils import timezone

class CouponCreateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def post(self, request):
        vendor = request.user  

        serializer = CouponSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(vendor=vendor) 
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

class VendorCouponListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]
    serializer_class = CouponSerializer

    def get_queryset(self):
        vendor = self.request.user  # Vendor instance
        return Coupon.objects.filter(vendor=vendor).order_by('-id')

class CouponListForUsers(generics.ListAPIView):
    serializer_class = CouponSerializeruser
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        now = timezone.now()
        vendor_id = self.request.query_params.get('vendor_id', None)

        queryset = Coupon.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now,
        )

        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)

        return queryset


class CouponRetrieveAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [AllowAny]
    lookup_field = 'pk'

class CouponListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.is_superuser or user.is_staff:
            coupons = Coupon.objects.all()
        else:
            try:
                vendor = Vendor.objects.get(id=user.id)
                coupons = Coupon.objects.filter(vendor=vendor)
            except Vendor.DoesNotExist:
                return Response({"error": "Vendor not found."}, status=404)

        serializer = CouponSerializer(coupons, many=True)
        return Response(serializer.data)
