from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import action
from foodproduct.models import Dish, DishAddOn
from foodproduct.serializers import *
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsAdminOrSuperuser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAdminUser
from vendors.authentication import VendorJWTAuthentication
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from vendors.pagination import CustomPageNumberPagination


class CustomFoodProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class DishCreateView(generics.ListCreateAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishCreateSerializer
    pagination_class = CustomFoodProductPagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]
    filter_backends = [SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        vendor = self.request.user
        return Dish.objects.filter(vendor=vendor)

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user)

class DishCreateViewAdmin(generics.ListCreateAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishCreateSerializer
    pagination_class=None
    permission_classes=[IsAdminUser]


class DishDetailViewAdmin(generics.RetrieveUpdateDestroyAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishCreateSerializer
    lookup_field = 'id'
    permission_classes=[IsAdminUser]

class ProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class DishListViewAdmin(generics.ListAPIView):
    serializer_class = DishCreateSerializer
    permission_classes = [IsAdminUser]
    pagination_class = ProductPagination

    def get_queryset(self):
        # Return products in LIFO order (newest first)
        return Dish.objects.all().order_by('-created_at')

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


class DishDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishCreateSerializer
    lookup_field = 'id'
    permission_classes=[IsAuthenticated]
    authentication_classes=[VendorJWTAuthentication]

class DishDetailViewUser(generics.RetrieveUpdateDestroyAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishCreateSerializer
    lookup_field = 'id'
    permission_classes=[]

class DishListView(generics.ListAPIView):
    queryset = Dish.objects.all()
    serializer_class = Dishlistserializer
    lookup_field = 'id'
    permission_classes=[]
    pagination_class=None

    def get_queryset(self):
        queryset = Dish.objects.all()
        is_veg_param = self.request.query_params.get('is_veg')

        if is_veg_param is not None:
            is_veg_bool = is_veg_param.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_veg=is_veg_bool)

        return queryset


class SingleDishDetailView(APIView):
    permission_classes = []
    def get(self, request, pk):
        try:
            dish = Dish.objects.get(pk=pk)
        except Dish.DoesNotExist:
            return Response({'error': 'Dish not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = Dishlistserializer(dish)
        return Response(serializer.data, status=status.HTTP_200_OK)

class VendorProductListView(APIView):
    permission_classes=[]
    def get(self, request, vendor_id):
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all products for this vendor
        products = Dish.objects.filter(vendor=vendor)
        serializer = DishCreateSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

#dish stats view
class DishStatsView(APIView):
    """
    API View to return counts of dishes based on different filters.
    """
    def get(self, request, *args, **kwargs):
        # Count dishes by various criteria
        total_dishes = Dish.objects.count()
        available_dishes = Dish.objects.filter(is_available=True).count()
        unavailable_dishes = Dish.objects.filter(is_available=False).count()
        popular_dishes = Dish.objects.filter(is_popular_product=True).count()
        offer_dishes = Dish.objects.filter(is_offer_product=True).count()

        # Prepare response data
        data = {
            "total_dishes": total_dishes,
            "available_dishes": available_dishes,
            "unavailable_dishes": unavailable_dishes,
            "popular_dishes": popular_dishes,
            "offer_dishes": offer_dishes
        }

        return Response(data, status=200)

class DishFilterListView(generics.ListAPIView):
    serializer_class = DishCreateSerializer
    permission_classes=[]
    def get_queryset(self):
        queryset = Dish.objects.all()
        vendor_id = self.kwargs.get('vendor_id', None)
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        category_id = self.kwargs.get('category_id', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        subcategory_id = self.kwargs.get('subcategory_id', None)
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)
        return queryset

#for listing offer product
from geopy.distance import geodesic

class DishOfferProductListView(generics.ListAPIView):
    serializer_class = DishCreateSerializer
    permission_classes = []
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        latitude = self.request.query_params.get("latitude")
        longitude = self.request.query_params.get("longitude")

        if not latitude or not longitude:
            return Dish.objects.none()

        user_location = (float(latitude), float(longitude))
        nearby_vendors = []

        for vendor in Vendor.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True):
            vendor_location = (float(vendor.latitude), float(vendor.longitude))
            distance_km = geodesic(user_location, vendor_location).km
            if distance_km <= 20:
                nearby_vendors.append(vendor.id)

        return Dish.objects.filter(
            vendor_id__in=nearby_vendors,
            is_offer_product=True
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

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

#for listing popular product
class DishPopularProductListView(generics.ListAPIView):
    serializer_class = DishCreateSerializer
    permission_classes=[]
    pagination_class = None
    def get_queryset(self):
        return Dish.objects.filter(is_popular_product=True)

class DishSearchFilterView(APIView):
    pagination_class = CustomFoodProductPagination
    permission_classes=[]

    def get(self, request):
        serializer = ProductSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        search_query = serializer.validated_data['search_query']

        products = Dish.objects.filter(name__icontains=search_query)

        if not products.exists():
            return Response({"detail": "No products found"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        paginated_products = paginator.paginate_queryset(products, request)

        product_serializer = DishCreateSerializer(paginated_products, many=True, context={'request': request})
        response_data = {
            'results': product_serializer.data,
            'count': products.count(),
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
        }

        return Response(response_data, status=status.HTTP_200_OK)

class DishAddOnCreateView(generics.CreateAPIView):
    queryset = DishAddOn.objects.all()
    serializer_class = DishAddOnSerializer
    permission_classes=[]

class DishAddOnListView(generics.ListAPIView):
    queryset = DishAddOn.objects.all()
    serializer_class = DishAddOnSerializer

class ReportDishView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        dish_id = data.get('dish')
        user = request.user
        reason = data.get('reason')

        # Validate the dish ID
        try:
            dish = Dish.objects.get(id=dish_id)
        except Dish.DoesNotExist:
            return Response({'error': 'Dish not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Create the report
        report = DishReport.objects.create(dish=dish, user=user, reason=reason)
        serializer = DishReportSerializer(report)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

# vendor admin
class ReportedDishListView(generics.ListAPIView):
    """
    List view for reported dishes.
    Only accessible by admins or authorized staff.
    """
    queryset = DishReport.objects.all()
    serializer_class = DishReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_resolved', 'dish__id', 'user__id']
    search_fields = ['reason', 'dish__name', 'user__username']
    ordering_fields = ['created_at', 'dish__name']
    ordering = ['-created_at']

class ResolveDishReportView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, *args, **kwargs):
        try:
            # Get the report by primary key
            dish_report = DishReport.objects.get(pk=pk)
        except DishReport.DoesNotExist:
            return Response({'error': 'Dish report not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Update the is_resolved field
        is_resolved = request.data.get('is_resolved', None)
        if is_resolved is not None:
            dish_report.is_resolved = is_resolved
            dish_report.save()
            return Response({'message': 'Dish report updated successfully.'}, status=status.HTTP_200_OK)

        return Response({'error': 'is_resolved field is required.'}, status=status.HTTP_400_BAD_REQUEST)

class ProductsBySubCategoryView(generics.ListAPIView):
    serializer_class = DishCreateSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination


    def get_queryset(self):
        subcategory_id = self.kwargs['subcategory_id']
        vendor_id = self.kwargs['vendor_id']
        return Dish.objects.filter(subcategory_id=subcategory_id, vendor_id=vendor_id)

class FoodImageListCreateViewVendor(generics.ListCreateAPIView):
    queryset = DishImage.objects.all()
    serializer_class = DishImageSerializer
    authentication_classes=[VendorJWTAuthentication]


class FoodImageDeleteView(APIView):
    authentication_classes=[VendorJWTAuthentication]

    def delete(self, request, image_id):
        image = get_object_or_404(DishImage, id=image_id)
        image.delete()
        return Response({"message": "Image deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class foodImageUpdateView(APIView):
    authentication_classes=[VendorJWTAuthentication]

    def patch(self, request, image_id):
        image_instance = get_object_or_404(DishImage, id=image_id)
        serializer = DishImageSerializer(image_instance, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)