from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from vendors.models import Vendor
from foodproduct.models import *
from foodproduct.serializers import *
from vendors.serializers import *
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsVendor
from rest_framework.permissions import AllowAny,IsAdminUser
from rest_framework.exceptions import NotFound
from vendors.pagination import CustomPageNumberPagination
from vendors.authentication import VendorJWTAuthentication
# View for Categories
class FoodCategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = FoodCategorySerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]


class FoodCategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = FoodCategorySerializer
    permission_classes = []

class FoodCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.all()
    serializer_class = FoodCategorySerializer
    authentication_classes = [VendorJWTAuthentication]


# View for SubCategories
class FoodSubCategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = FoodSubCategories.objects.all()
    serializer_class = FoodSubCategorycreateSerializer
    authentication_classes = [VendorJWTAuthentication]
    pagination_class = None

class FoodSubCategoryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = FoodSubCategories.objects.all()
    serializer_class = FoodSubCategorySerializer
    authentication_classes = [VendorJWTAuthentication]
    pagination_class = None
    def get_queryset(self):
        return FoodSubCategories.objects.filter(vendor=self.request.user)

class FoodSubCategoryListViewAdmin(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    queryset = FoodSubCategories.objects.all()
    serializer_class = FoodSubCategorySerializer
    pagination_class = None

class FoodSubCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = FoodSubCategories.objects.all()
    serializer_class = FoodSubCategorySerializer
    authentication_classes = [VendorJWTAuthentication]


class VendorByCategoryView(generics.ListAPIView):
    serializer_class = VendorSerializer
    permission_classes = []

    def get_queryset(self):
        category_name = self.request.query_params.get('category_name', None)
        if not category_name:
            raise NotFound("Category name is required.")
        categories = Category.objects.filter(name__icontains=category_name)
        if not categories.exists():
            raise NotFound("No categories found with the given name.")
        vendor_ids = FoodSubCategories.objects.filter(
            category__in=categories
        ).values_list('vendor', flat=True)
        vendors = Vendor.objects.filter(id__in=vendor_ids, is_active=True, is_approved=True)
        if not vendors.exists():
            raise NotFound("No vendors found for the given category.")
        return vendors

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class VendorBySubCategoryView(generics.ListAPIView):
    serializer_class = VendorSerializer
    permission_classes = []

    def get_queryset(self):
        subcategory_name = self.request.query_params.get('subcategory_name', None)
        if not subcategory_name:
            raise NotFound("Subcategory name is required.")
        subcategories = FoodSubCategories.objects.filter(name__icontains=subcategory_name, enable_subcategory=True)
        if not subcategories.exists():
            raise NotFound("No subcategories found with the given name.")
        vendor_ids = subcategories.values_list('vendor', flat=True).distinct()
        vendors = Vendor.objects.filter(id__in=vendor_ids, is_active=True, is_approved=True)
        if not vendors.exists():
            raise NotFound("No vendors found for the given subcategory.")
        return vendors

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class VendorCategoryListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes=[VendorJWTAuthentication]
    def get(self, request, vendor_id):
        try:
            vendor = Vendor.objects.get(id=vendor_id)
            categories = Category.objects.filter(
                food_subcategories__vendor=vendor
            ).distinct()
            serializer = CategorySerializer(categories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Vendor.DoesNotExist:
            return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

class VendorFoodSubCategoryListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def get(self, request, vendor_id):
        try:
            vendor = Vendor.objects.get(id=vendor_id)
            subcategories = FoodSubCategories.objects.filter(vendor=vendor, enable_subcategory=True)
            serializer = FoodSubCategorySerializer(subcategories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Vendor.DoesNotExist:
            return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

class VendorsByCategoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, category_id, *args, **kwargs):
        # Retrieve the food category by ID
        category = Category.objects.filter(id=category_id).first()

        if category:
            # Get the vendor associated with the category
            vendor = category.store
            # Check if the store_logo exists and handle accordingly
            store_logo_url = vendor.store_logo.url if vendor.store_logo else None
            # Prepare the vendor data
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

class FoodSubCategoryListByCategory(generics.ListAPIView):
    serializer_class = FoodSubCategorySerializer
    pagination_class = CustomPageNumberPagination
    authentication_classes = [VendorJWTAuthentication]

    def get_queryset(self):
        category_id = self.kwargs['category_id']
        vendor = self.request.user

        # Optional: Check category exists
        if not Category.objects.filter(id=category_id).exists():
            raise PermissionDenied("Category does not exist.")

        # If your FoodSubCategories model has a vendor field
        return FoodSubCategories.objects.filter(
            category_id=category_id,
            vendor=vendor  # Only if vendor field exists
        )