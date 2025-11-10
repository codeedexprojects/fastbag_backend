from rest_framework import generics
from fashion.models import *
from fashion.serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser,AllowAny,IsAuthenticated
from vendors.authentication import VendorJWTAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from vendors.serializers import *
from rest_framework.filters import SearchFilter
from vendors.pagination import CustomPageNumberPagination
from rest_framework.pagination import PageNumberPagination



class ColorCreateView(generics.CreateAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    pagination_class = None
    permission_classes = [IsAdminUser]

class ColorListView(generics.ListAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    pagination_class = None
    permission_classes = [IsAdminUser]


class ColorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    pagination_class = None
    permission_classes = [IsAdminUser]

class ClothingListCreateView(generics.ListCreateAPIView):
    queryset = Clothing.objects.all()
    serializer_class = ClothingSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]
    filter_backends = [SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        vendor = self.request.user
        return Clothing.objects.filter(vendor=vendor)

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user)


class ClothingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Clothing.objects.all()
    serializer_class = ClothingSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

#admin
class ClothingListCreateViewAdmin(generics.ListCreateAPIView):
    queryset = Clothing.objects.all()
    serializer_class = ClothingSerializer
    permission_classes = [IsAdminUser]
    pagination_class=None

from geopy.distance import geodesic

class OfferProductsViewfashion(generics.ListAPIView):
    serializer_class = ClothingSerializer
    permission_classes = []
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        latitude = self.request.query_params.get("latitude")
        longitude = self.request.query_params.get("longitude")

        if not latitude or not longitude:
            return Clothing.objects.none()

        user_location = (float(latitude), float(longitude))
        nearby_vendors = []

        for vendor in Vendor.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True):
            vendor_location = (float(vendor.latitude), float(vendor.longitude))
            distance_km = geodesic(user_location, vendor_location).km
            if distance_km <= 20:  # within 20 km
                nearby_vendors.append(vendor.id)

        return Clothing.objects.filter(
            vendor_id__in=nearby_vendors,
            is_offer_product=True,
            is_active=True,
            is_available=True
        )

    def list(self, request, *args, **kwargs):
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")

        if not latitude or not longitude:
            return Response(
                {"error": "Latitude and longitude are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Fallback: no pagination
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

#admin
class ClothingImageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ClothingImage.objects.all()
    serializer_class = ClothingImageSerializer
    permission_classes = [IsAdminUser]
    pagination_class=None

#debug
    # def list(self, request, *args, **kwargs):
    #     print("Request data in list method:", request.data)
    #     return super().list(request, *args, **kwargs)

class ProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ClothingListViewAdmin(generics.ListAPIView):
    serializer_class = ClothingSerializer
    permission_classes = [IsAdminUser]
    pagination_class = ProductPagination

    def get_queryset(self):
        # Return products in LIFO order (newest first)
        return Clothing.objects.all().order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get total count before pagination
        total_count = queryset.count()
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            
            # Calculate the starting serial number for this page
            page_number = self.paginator.page.number
            page_size = self.paginator.page_size
            start_index = total_count - ((page_number - 1) * page_size)
            
            # Add serial numbers to each item
            data_with_serial = []
            for i, item in enumerate(serializer.data):
                item['serial_number'] = start_index - i
                data_with_serial.append(item)
            
            return self.get_paginated_response(data_with_serial)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class ClothingDetailViewAdmin(generics.RetrieveUpdateDestroyAPIView):
    queryset = Clothing.objects.all()
    serializer_class = ClothingSerializer
    permission_classes = [IsAdminUser]
    # parser_classes = [MultiPartParser, FormParser]

class ClothingDetailViewUser(generics.RetrieveUpdateDestroyAPIView):
    queryset = Clothing.objects.all()
    serializer_class = ClothingSerializer
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser]

class ClothingImageListCreateViewVendor(generics.ListCreateAPIView):
    queryset = ClothingImage.objects.all()
    serializer_class = ClothingImageSerializer
    authentication_classes=[VendorJWTAuthentication]

class ClothingListViewUser(generics.ListAPIView):
    queryset = Clothing.objects.all()
    serializer_class = ClothingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class=None


class ClothingImageListCreateView(generics.ListCreateAPIView):
    queryset = ClothingImage.objects.all()
    serializer_class = ClothingImageSerializer
    permission_classes = [IsAdminUser]


class ClothingImageDeleteView(APIView):
    authentication_classes=[VendorJWTAuthentication]

    def delete(self, request, image_id):
        """
        Deletes a specific image by its ID.
        """
        image = get_object_or_404(ClothingImage, id=image_id)
        image.delete()
        return Response({"message": "Image deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class ClothingImageUpdateView(APIView):
    authentication_classes=[VendorJWTAuthentication]

    def patch(self, request, image_id):
        image_instance = get_object_or_404(ClothingImage, id=image_id)
        serializer = ClothingImageSerializer(image_instance, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProductsByCategorySubCategoryView(generics.ListAPIView):
    serializer_class = ClothingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        category_id = self.kwargs['category_id']
        subcategory_id = self.kwargs['subcategory_id']
        vendor_id = self.kwargs['vendor_id']
        return Clothing.objects.filter(
            category_id=category_id,
            subcategory_id=subcategory_id,
            vendor_id=vendor_id,
            is_active=True
        )


#search
class SearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()

        # Search Categories
        categories = ClothingCategory.objects.filter(name__icontains=query, is_active=True)
        categories_data = ClothingCategorySerializer(categories, many=True).data

        # Search Subcategories
        subcategories = SubCategory.objects.filter(name__icontains=query, is_active=True)
        subcategories_data = SubCategorySerializer(subcategories, many=True).data

        # Search Products
        products = Clothing.objects.filter(name__icontains=query, is_active=True)
        products_data = ClothingSerializer(products, many=True).data

        return Response({
            'categories': categories_data,
            'subcategories': subcategories_data,
            'products': products_data
        })

class ClothingProductCountView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        count = Clothing.objects.count()
        return Response({'total_products': count})

#products by vendor
class ProductsByvendor(generics.ListAPIView):
    serializer_class = ClothingSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_id']
        return Clothing.objects.filter(vendor_id=vendor_id, is_active=True)