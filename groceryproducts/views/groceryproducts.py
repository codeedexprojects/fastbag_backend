from rest_framework import generics
from groceryproducts.models import *
from groceryproducts.serializers import *
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated,AllowAny,IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from vendors.authentication import VendorJWTAuthentication
from django.shortcuts import get_object_or_404
from vendors.pagination import CustomPageNumberPagination


class ProductPagination(PageNumberPagination):
    """
    Custom pagination for products.
    """
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allow client to set page size
    max_page_size = 100  # Maximum page size

class GroceryProductCreateView(generics.ListCreateAPIView):
    queryset = GroceryProducts.objects.all().order_by('-created_at')
    serializer_class = GroceryProductSerializer
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['name']

    def perform_create(self, serializer):
        product = serializer.save()
        images_data = self.request.FILES.getlist('images')
        for image in images_data:
            GroceryProductImage.objects.create(product=product, image=image)
#admin

class GroceryProductCreateViewAdmin(generics.ListCreateAPIView):
    queryset = GroceryProducts.objects.all().order_by('-created_at')
    serializer_class = GroceryProductSerializer
    permission_classes=[IsAdminUser]
    pagination_class=None

    def perform_create(self, serializer):
        product = serializer.save()
        images_data = self.request.FILES.getlist('images')
        for image in images_data:
            GroceryProductImage.objects.create(product=product, image=image)

class ProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class groceryproductlistviewadmin(generics.ListAPIView):
    serializer_class = GroceryProductSerializer
    permission_classes = [IsAdminUser]
    pagination_class = ProductPagination

    def get_queryset(self):
        # Return products in LIFO order (newest first)
        return GroceryProducts.objects.all().order_by('-created_at')

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

#product details
class GroceryProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GroceryProducts.objects.all()
    serializer_class = GroceryProductSerializer
    pagination_class = None
    authentication_classes = [VendorJWTAuthentication]

    def retrieve(self, request, *args, **kwargs):

        try:
            product = self.get_object()
            serializer = self.get_serializer(product)
            return Response({
                'message': 'Product retrieved successfully!',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except GroceryProducts.DoesNotExist:
            return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop('partial', False)
        try:
            product = self.get_object()

            images_data = request.FILES.getlist('images')

            serializer = self.get_serializer(product, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            if images_data:
                product.images.all().delete()

                for image_file in images_data:
                    GroceryProductImage.objects.create(product=product, image=image_file)

            updated_serializer = self.get_serializer(product)
            return Response({
                'message': 'Product updated successfully!',
                'data': updated_serializer.data
            }, status=status.HTTP_200_OK)
        except GroceryProducts.DoesNotExist:
            return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


    def destroy(self, request, *args, **kwargs):
        """
        Handle DELETE request to delete a product
        """
        try:
            product = self.get_object()
            self.perform_destroy(product)
            return Response({
                'message': 'Product deleted successfully!'
            }, status=status.HTTP_200_OK)
        except GroceryProducts.DoesNotExist:
            return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

#admin

class GroceryProductDetailViewAdmin(generics.RetrieveUpdateDestroyAPIView):
    queryset = GroceryProducts.objects.all()
    serializer_class = GroceryProductSerializer
    pagination_class = None
    permission_classes = [IsAdminUser]

    def retrieve(self, request, *args, **kwargs):
        """
        Handle GET request to retrieve a product
        """
        try:
            product = self.get_object()
            serializer = self.get_serializer(product)
            return Response({
                'message': 'Product retrieved successfully!',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except GroceryProducts.DoesNotExist:
            return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        """
        Handle PUT or PATCH request to update a product, including handling image uploads.
        """
        partial = kwargs.pop('partial', False)
        try:
            product = self.get_object()

            images_data = request.FILES.getlist('images')

            serializer = self.get_serializer(product, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            if images_data:
                product.images.all().delete()

                for image_file in images_data:
                    GroceryProductImage.objects.create(product=product, image=image_file)

            updated_serializer = self.get_serializer(product)
            return Response({
                'message': 'Product updated successfully!',
                'data': updated_serializer.data
            }, status=status.HTTP_200_OK)
        except GroceryProducts.DoesNotExist:
            return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


    def destroy(self, request, *args, **kwargs):
        """
        Handle DELETE request to delete a product
        """
        try:
            product = self.get_object()
            self.perform_destroy(product)
            return Response({
                'message': 'Product deleted successfully!'
            }, status=status.HTTP_200_OK)
        except GroceryProducts.DoesNotExist:
            return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

#for listing offer product
from geopy.distance import geodesic

class GroceryOfferProductListView(generics.ListAPIView):
    serializer_class = GroceryProductSerializer
    permission_classes = []
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        latitude = self.request.query_params.get("latitude")
        longitude = self.request.query_params.get("longitude")

        if not latitude or not longitude:
            return GroceryProducts.objects.none()

        user_location = (float(latitude), float(longitude))
        nearby_vendors = []

        for vendor in Vendor.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True):
            vendor_location = (float(vendor.latitude), float(vendor.longitude))
            distance_km = geodesic(user_location, vendor_location).km
            if distance_km <= 20:
                nearby_vendors.append(vendor.id)

        return GroceryProducts.objects.filter(
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
class GroceryPopularProductListView(generics.ListAPIView):
    serializer_class = GroceryProductSerializer
    pagination_class = None
    permission_classes=[]
    def get_queryset(self):
        return GroceryProducts.objects.filter(is_popular_product=True)

#for seraching products
class ProductSearchFilterView(APIView):
    permission_classes = []
    pagination_class = ProductPagination

    def get(self, request):
        serializer = ProductSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        search_query = serializer.validated_data['search_query']

        products = GroceryProducts.objects.filter(name__icontains=search_query)

        if not products.exists():
            return Response({"detail": "No products found"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()  # Use the defined pagination class
        paginated_products = paginator.paginate_queryset(products, request, view=self)

        product_serializer = GroceryProductSerializer(paginated_products, many=True, context={'request': request})
        response_data = {
            'results': product_serializer.data,
            'count': products.count(),
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
        }

        return Response(response_data, status=status.HTTP_200_OK)

class GroceryProductListView(generics.ListAPIView):
    queryset = GroceryProducts.objects.all()
    serializer_class = GroceryProductSerializer
    lookup_field = 'id'
    permission_classes=[]
    pagination_class =ProductPagination

class GroceryProductStatsView(APIView):
    """
    API View to return counts of dishes based on different filters.
    """
    def get(self, request, *args, **kwargs):
        # Count dishes by various criteria
        total_products = GroceryProducts.objects.count()
        available_products = GroceryProducts.objects.filter(Available=True).count()
        unavailable_products= GroceryProducts.objects.filter(Available=False).count()
        popular_products = GroceryProducts.objects.filter(is_popular_product=True).count()
        offer_products = GroceryProducts.objects.filter(is_offer_product=True).count()

        # Prepare response data
        data = {
            "total_products": total_products,
            "available_products": available_products,
            "unavailable_products": unavailable_products,
            "popular_products": popular_products,
            "offer_products": offer_products
        }

        return Response(data, status=200)

class GroceryProductListView(APIView):
    permission_classes=[]
    def get(self, request, vendor_id):
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all products for this vendor
        products = GroceryProducts.objects.filter(vendor=vendor)
        serializer = GroceryProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class Allgroceryproducts(generics.ListAPIView):
    queryset = GroceryProducts.objects.all().order_by('-created_at')
    serializer_class = GroceryProductSerializer
    pagination_class = ProductPagination
    permission_classes = [AllowAny]

class ReportGroceryProductView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        grocery_product_id = data.get('grocery_product')  # Ensure the key matches the field name
        user = request.user
        reason = data.get('reason')

        # Validate the grocery product ID
        try:
            grocery_product = GroceryProducts.objects.get(id=grocery_product_id)
        except GroceryProducts.DoesNotExist:
            return Response(
                {'error': 'Grocery product not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create the report
        report = GroceryProductReport.objects.create(
            grocery_product=grocery_product,  # Use the correct field name
            user=user,
            reason=reason
        )

        serializer = GroceryProductReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ReportedGroceryProductListView(generics.ListAPIView):

    queryset = GroceryProductReport.objects.all()
    serializer_class = GroceryProductReportSerializer
    permission_classes = [IsAuthenticated]  # Only authenticated users can access
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_resolved', 'grocery_product__id', 'user__id']  # Filter by product, user, resolution status
    search_fields = ['reason', 'grocery_product__name', 'user__username']  # Search by reason, product name, or username
    ordering_fields = ['created_at', 'grocery_product__name']  # Allow ordering by creation date or product name
    ordering = ['-created_at']  # Default ordering: latest first

class ResolveGroceryProductReportView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, *args, **kwargs):
        try:
            # Get the report by primary key
            grocery_report = GroceryProductReport.objects.get(pk=pk)
        except GroceryProductReport.DoesNotExist:
            return Response({'error': 'Grocery product report not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Update the is_resolved field
        is_resolved = request.data.get('is_resolved', None)
        if is_resolved is not None:
            grocery_report.is_resolved = is_resolved
            grocery_report.save()
            return Response({'message': 'Grocery product report updated successfully.'}, status=status.HTTP_200_OK)

        return Response({'error': 'is_resolved field is required.'}, status=status.HTTP_400_BAD_REQUEST)

class GroceryProductsBySubcategoryVendorView(generics.ListAPIView):
    serializer_class = GroceryProductSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        vendor_id = self.kwargs.get('vendor_id')
        sub_category_id = self.kwargs.get('sub_category_id')

        if not vendor_id or not sub_category_id:
            return GroceryProducts.objects.none()

        return GroceryProducts.objects.filter(vendor_id=vendor_id, subcategory_id=sub_category_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductsBySubCategoryView(generics.ListAPIView):
    serializer_class = GroceryProductSerializer
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination


    def get_queryset(self):
        subcategory_id = self.kwargs['subcategory_id']
        vendor_id = self.kwargs['vendor_id']
        return GroceryProducts.objects.filter(subcategory_id=subcategory_id, vendor_id=vendor_id)

class GroceryImageListCreateViewVendor(generics.ListCreateAPIView):
    queryset = GroceryProductImage.objects.all()
    serializer_class = GroceryProductImageSerializer
    authentication_classes=[VendorJWTAuthentication]

class GroceryImageDeleteView(APIView):
    authentication_classes=[VendorJWTAuthentication]

    def delete(self, request, image_id):
        image = get_object_or_404(GroceryProductImage, id=image_id)
        image.delete()
        return Response({"message": "Image deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class GroceryImageUpdateView(APIView):
    authentication_classes=[VendorJWTAuthentication]

    def patch(self, request, image_id):
        image_instance = get_object_or_404(GroceryProductImage, id=image_id)
        serializer = GroceryProductImageSerializer(image_instance, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GroceryProductDetailViewUser(generics.RetrieveUpdateDestroyAPIView):
    queryset = GroceryProducts.objects.all()
    serializer_class = GroceryProductSerializer
    pagination_class = None
    permission_classes=[]