from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from foodproduct.models import *
from foodproduct.serializers import *
from users.permissions import * 
class VendorBannerFoodProductsCreateAPIView(generics.CreateAPIView):
    queryset = VendorBannerFoodProducts.objects.all()
    serializer_class = VendorBannerFoodProductsSerializer
    permission_classes = [IsSuperUserOrAdmin]

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

class VendorBannerFoodProductsRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VendorBannerFoodProducts.objects.all()
    serializer_class = VendorBannerFoodProductsSerializer
    lookup_field = 'pk'  
    permission_classes = [IsSuperUserOrAdmin]

    def get(self, request, *args, **kwargs):
        # Retrieve the banner
        return super().get(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        # Update the banner
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Delete the banner
        return super().destroy(request, *args, **kwargs)

class VendorBannerFoodProductsListView(generics.ListAPIView):
    """
    List view for VendorBannerFoodProducts.
    Only accessible by superusers.
    """
    queryset = VendorBannerFoodProducts.objects.all()
    serializer_class = VendorBannerFoodProductsSerializer
    permission_classes = [IsAuthenticated, IsSuperUserOrAdmin]