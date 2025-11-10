from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from groceryproducts.models import *
from foodproduct.models import *
from users.serializers import *
from foodproduct.serializers import *
from groceryproducts.serializers import *
from rest_framework import viewsets
from fashion.models import *
from fashion.serializers import ClothingSerializer
from foodproduct.serializers import DishCreateSerializer
from fashion.serializers import *
from rest_framework import generics
from rest_framework.permissions import AllowAny,IsAuthenticated
from vendors.pagination import CustomPageNumberPagination
from datetime import timedelta
from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from vendors.serializers import SubCategorySerializer


class UnifiedProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class UnifiedProductListView(viewsets.ViewSet):
    pagination_class = UnifiedProductPagination
    permission_classes=[]

    def list(self, request):
        # Fetch products from both models
        dishes = Dish.objects.all()
        grocery_products = GroceryProducts.objects.all()

        # Combine both QuerySets
        combined_products = list(dishes) + list(grocery_products)

        # Apply pagination
        paginator = self.pagination_class()
        paginated_products = paginator.paginate_queryset(combined_products, request)

        # Serialize the data
        serializer = UnifiedProductSerializer(paginated_products, many=True, context={'selected_weight': request.query_params.get('selected_weight')})

        return paginator.get_paginated_response(serializer.data)

class UnifiedCategoryListView(APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        # Retrieve all categories for different types
        food_categories = Category.objects.filter(category_type='food')
        grocery_categories = Category.objects.filter(category_type='grocery')
        fashion_categories = Category.objects.filter(category_type='fashion')

        # Combine the querysets
        combined_queryset = list(food_categories) + list(grocery_categories) + list(fashion_categories)

        # Serialize the data
        serializer = UnifiedCategoryListSerializer(combined_queryset, many=True)

        # Return the response with all data
        return Response(serializer.data)

class ProductsByCategoryView(APIView):
    permission_classes=[]
    def get(self, request, category_id):
        grocery_products = GroceryProducts.objects.filter(category_id=category_id)
        clothing_products = Clothing.objects.filter(category_id=category_id)
        dish_products = Dish.objects.filter(category_id=category_id)

        grocery_data = GroceryProductSerializer(grocery_products, many=True).data
        clothing_data = ClothingSerializer(clothing_products, many=True).data
        dish_data = DishCreateSerializer(dish_products, many=True).data

        all_products = {
            "grocery_products": grocery_data,
            "clothing_products": clothing_data,
            "dish_products": dish_data
        }

        return Response(all_products, status=status.HTTP_200_OK)

class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

class SubcategoriesByCategoryView(APIView):
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination

    def paginate_queryset(self, queryset, request):
        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        return paginated_qs, paginator

    def get(self, request, category_id):
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response({"detail": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

        clothing_qs = SubCategory.objects.filter(category=category, is_active=True)
        if clothing_qs.exists():
            page, paginator = self.paginate_queryset(clothing_qs, request)
            serializer = SubCategorySerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        food_qs = SubCategory.objects.filter(category=category, is_active=True)
        if food_qs.exists():
            page, paginator = self.paginate_queryset(food_qs, request)
            serializer = SubCategorySerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        grocery_qs = SubCategory.objects.filter(category=category, is_active=True)
        if grocery_qs.exists():
            page, paginator = self.paginate_queryset(grocery_qs, request)
            serializer = SubCategorySerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        return Response({"detail": "No subcategories found for this category"}, status=status.HTTP_204_NO_CONTENT)

class ProductsBySubcategoryView(APIView):
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination

    def get(self, request, subcategory_type, subcategory_id):
        try:
            paginator = self.pagination_class()

            if subcategory_type == 'Grocery':
                products = GroceryProducts.objects.filter(subcategory_id=subcategory_id, is_available=True)
                result_page = paginator.paginate_queryset(products, request)
                serializer = GroceryProductSerializer(result_page, many=True, context={'request': request})  # Add context
                return paginator.get_paginated_response(serializer.data)

            elif subcategory_type == 'Restaurent':
                dishes = Dish.objects.filter(subcategory_id=subcategory_id, is_available=True).prefetch_related('images')
                result_page = paginator.paginate_queryset(dishes, request)
                serializer = DishCreateSerializer(result_page, many=True, context={'request': request})  # Already correct
                return paginator.get_paginated_response(serializer.data)

            elif subcategory_type == 'Fashion':
                clothes = Clothing.objects.filter(subcategory_id=subcategory_id, is_active=True)
                result_page = paginator.paginate_queryset(clothes, request)
                serializer = ClothingSerializer(result_page, many=True, context={'request': request})  # Add context
                return paginator.get_paginated_response(serializer.data)

            else:
                return Response({"detail": "Invalid subcategory type"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class SubCategoriesByVendorAPIView(APIView):
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination

    def get(self, request, vendor_id):
        subcategory_ids = set()

        # 1. From GroceryProducts
        grocery_subs = GroceryProducts.objects.filter(vendor_id=vendor_id).values_list('subcategory_id', flat=True)

        # 2. From Dishes
        food_subs = Dish.objects.filter(vendor_id=vendor_id).values_list('subcategory_id', flat=True)

        # 3. From Clothing
        clothing_subs = Clothing.objects.filter(vendor_id=vendor_id).values_list('subcategory_id', flat=True)

        # Combine all unique subcategory IDs
        subcategory_ids.update(grocery_subs)
        subcategory_ids.update(food_subs)
        subcategory_ids.update(clothing_subs)

        # Get actual SubCategory instances (only active ones)
        subcategories = SubCategory.objects.filter(id__in=subcategory_ids, is_active=True)

        # Serialize and paginate
        paginator = self.pagination_class()
        paginated = paginator.paginate_queryset(subcategories, request, view=self)
        serialized = SubCategorySerializer(paginated, many=True, context={'request': request})

        return paginator.get_paginated_response(serialized.data)




#Big buy
class BigBuyOrderCreateView(generics.CreateAPIView):
    queryset = BigBuyOrder.objects.all()
    serializer_class = BigBuyOrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class BigBuyOrderListView(generics.ListAPIView):
    serializer_class = BigBuyOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BigBuyOrder.objects.filter(user=self.request.user)

class BigBuyOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BigBuyOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BigBuyOrder.objects.filter(user=self.request.user)

#  Admin: List all Big Buy orders
class AdminBigBuyOrderListView(generics.ListAPIView):
    queryset = BigBuyOrder.objects.all().order_by('-created_at')
    serializer_class = BigBuyOrderSerializer
    permission_classes = [IsAdminUser]


# Retrieve a specific Big Buy order
class AdminBigBuyOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BigBuyOrder.objects.all()
    serializer_class = BigBuyOrderSerializer
    permission_classes = [IsAdminUser]


#  Update a specific Big Buy order (e.g., status)
class AdminBigBuyOrderUpdateView(generics.UpdateAPIView):
    queryset = BigBuyOrder.objects.all()
    serializer_class = BigBuyOrderSerializer
    permission_classes = [IsAdminUser]


class CancelBigBuyOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = BigBuyOrder.objects.get(id=order_id, user=request.user)
        except BigBuyOrder.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        if order.status != 'PENDING':
            return Response({"detail": "Only 'PENDING' orders can be cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        cancel_reason = request.data.get("cancel_reason", "").strip()
        if not cancel_reason:
            return Response({"detail": "Cancellation reason is required."}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'CANCELLED'
        order.cancel_reason = cancel_reason
        order.save()

        return Response({"detail": "Order cancelled successfully."}, status=status.HTTP_200_OK)