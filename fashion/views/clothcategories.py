from rest_framework import generics
from fashion.serializers import *
from rest_framework.permissions import IsAdminUser,AllowAny
from vendors.models import Category
from vendors.authentication import VendorJWTAuthentication
from rest_framework.pagination import PageNumberPagination
from vendors.pagination import CustomPageNumberPagination
from vendors.serializers import SubCategorySerializer


class ClothingCategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    queryset = Category.objects.all()
    serializer_class = ClothingCategorySerializer
    pagination_class = None

class ClothingCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = ClothingCategorySerializer
    permission_classes = [IsAdminUser]
    pagination_class = None


class ClothingSubCategoryListCreateView(generics.ListCreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    pagination_class = None
    authentication_classes = [VendorJWTAuthentication]


    def perform_create(self, serializer):
        serializer.save()

class ClothingSubCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    pagination_class = None
    authentication_classes = [VendorJWTAuthentication]


class ProductsByCategoryView(generics.ListAPIView):
    serializer_class = ClothingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        category_id = self.kwargs['category_id']
        vendor_id = self.kwargs['vendor_id']
        return Clothing.objects.filter(category_id=category_id, vendor_id=vendor_id, is_active=True)

class ProductsBySubCategoryView(generics.ListAPIView):
    serializer_class = ClothingSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        subcategory_id = self.kwargs['subcategory_id']
        vendor_id = self.kwargs['vendor_id']
        return Clothing.objects.filter(subcategory_id=subcategory_id, vendor_id=vendor_id)

from rest_framework.exceptions import PermissionDenied

class ClothingSubCategoryListByCategory(generics.ListAPIView):
    serializer_class = SubCategorySerializer
    pagination_class = CustomPageNumberPagination
    authentication_classes = [VendorJWTAuthentication]

    def get_queryset(self):
        category_id = self.kwargs['category_id']
        # vendor = self.request.user


        if not Category.objects.filter(id=category_id).exists():
            raise PermissionDenied("Category does not exist.")


        return SubCategory.objects.filter(
            category_id=category_id,
            # vendor=vendor
        )

