from django.shortcuts import render
from rest_framework.pagination import PageNumberPagination
from rest_framework import generics
from groceryproducts.models import *
from groceryproducts.serializers import *
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny,IsAdminUser
from rest_framework.exceptions import NotFound
from vendors.serializers import *
from vendors.authentication import VendorJWTAuthentication
from vendors.pagination import CustomPageNumberPagination

class CustomGorceryProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

#category
from rest_framework.parsers import MultiPartParser, FormParser

class GroceryCategoryListView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    def post(self, request, *args, **kwargs):
        data = request.data
        if 'image' in request.FILES:
            data['image'] = request.FILES['image']
        serializer = GroceryCategorySerializer(data=data, context={'request': request})

        if serializer.is_valid():
            grocery_category = serializer.save()
            return Response(GroceryCategorySerializer(grocery_category, context={'request': request}).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class Gro_CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = GroceryCategorySerializer
    pagination_class = None
    permission_classes = []

class GroceryCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = GroceryCategorySerializer
    pagination_class = None
    permission_classes = [IsAuthenticated]

#sub category
class GrocerySubCategoryListView(generics.ListCreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    pagination_class = None
    authentication_classes = [VendorJWTAuthentication]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        return SubCategory.objects.filter(vendor=self.request.user)

class GrocerySubCategoryListViewAdmin(generics.ListCreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    pagination_class = None
    permission_classes = [IsAdminUser]
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class Gro_SubCategoryListView(generics.ListAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    pagination_class=None
    permission_classes=[]

class GrocerySubCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    pagination_class = None
    authentication_classes = [VendorJWTAuthentication]

class GroVendorByCategoryView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = VendorSerializer  # Assume VendorSerializer is defined to serialize Vendor details

    def get_queryset(self):
        category_name = self.request.query_params.get('category_name', None)
        if not category_name:
            raise NotFound("Category name is required.")

        # Fetch categories matching the name and enabled status
        categories = Category.objects.filter(name__icontains=category_name, Enable_category=True)
        if not categories.exists():
            raise NotFound("No categories found with the given name.")

        # Get vendor IDs associated with the matching categories
        vendor_ids = categories.values_list('store', flat=True)  # Assuming `store` links to Vendor
        vendors = Vendor.objects.filter(id__in=vendor_ids, is_active=True, is_approved=True)

        return vendors

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class GroVendorBySubcategoryView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = VendorSerializer

    def get_queryset(self):
        subcategory_name = self.request.query_params.get('subcategory_name', None)
        if not subcategory_name:
            raise NotFound("Subcategory name is required.")

        subcategories = SubCategory.objects.filter(name__icontains=subcategory_name, Enable_subcategory=True)
        if not subcategories.exists():
            raise NotFound("No subcategories found with the given name.")

        category_ids = subcategories.values_list('Category', flat=True)
        vendor_ids = Category.objects.filter(id__in=category_ids).values_list('store', flat=True)
        vendors = Vendor.objects.filter(id__in=vendor_ids, is_active=True, is_approved=True)

        return vendors

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class VendorsByGroceryCategoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, category_id, *args, **kwargs):
        category = Category.objects.filter(id=category_id).first()

        if category:
            vendor = category.store
            store_logo_url = vendor.store_logo.url if vendor.store_logo else None
            vendor_data = {
                'vendor_name': vendor.business_name,
                'location': vendor.business_location,
                'opening_time': vendor.opening_time,
                'closing_time': vendor.closing_time,
                'store_logo': store_logo_url
            }
            return Response(vendor_data)
        else:
            return Response({"detail": "Category not found"}, status=404)

from rest_framework.exceptions import PermissionDenied
class GrocerySubCategoryListByCategory(generics.ListAPIView):
    serializer_class = SubCategorySerializer
    pagination_class = CustomPageNumberPagination
    authentication_classes = [VendorJWTAuthentication]

    def get_queryset(self):
        category_id = self.kwargs['category_id']
        vendor = self.request.user

        if not Category.objects.filter(id=category_id).exists():
            raise PermissionDenied("Category does not exist.")

        return SubCategory.objects.filter(
            category_id=category_id,
            grocery__vendor=vendor
        )
