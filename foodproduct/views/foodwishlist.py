from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from foodproduct.models import *
from rest_framework.permissions import IsAuthenticated
from foodproduct.serializers import *
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from vendors.authentication import VendorJWTAuthentication

class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wishlist_items = Wishlist.objects.filter(user=request.user)
        serializer = WishlistSerializer(wishlist_items, many=True)
        return Response(serializer.data)

    def post(self, request):
        dish_id = request.data.get('dish')
        try:
            dish = Dish.objects.get(id=dish_id)
        except Dish.DoesNotExist:
            return Response({"detail": "Dish not found."}, status=status.HTTP_404_NOT_FOUND)

        if Wishlist.objects.filter(user=request.user, dish=dish).exists():
            return Response({"detail": "Dish already in the wishlist."}, status=status.HTTP_400_BAD_REQUEST)

        wishlist_item = Wishlist.objects.create(user=request.user, dish=dish)

        dish.is_wishlisted = True
        dish.save(update_fields=["is_wishlisted"])

        serializer = WishlistSerializer(wishlist_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        dish_id = request.data.get('dish')
        try:
            dish = Dish.objects.get(id=dish_id)
        except Dish.DoesNotExist:
            return Response({"detail": "Dish not found."}, status=status.HTTP_404_NOT_FOUND)

        wishlist_item = Wishlist.objects.filter(user=request.user, dish=dish).first()
        if wishlist_item:
            wishlist_item.delete()

            if not Wishlist.objects.filter(dish=dish).exists():
                dish.is_wishlisted = False
                dish.save(update_fields=["is_wishlisted"])

            return Response({"detail": "Dish removed from wishlist."}, status=status.HTTP_204_NO_CONTENT)

        return Response({"detail": "Dish not in the wishlist."}, status=status.HTTP_400_BAD_REQUEST)

class DishReviewCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DishReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class DishReviewDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, review_id):
        try:
            review = DishReview.objects.get(id=review_id, user=request.user)
        except DishReview.DoesNotExist:
            return Response({"error": "Review not found or you do not have permission to delete it."},
                            status=status.HTTP_404_NOT_FOUND)

        review.delete()
        return Response({"message": "Review deleted successfully."}, status=status.HTTP_200_OK)

class ListFoodProductReviewsView(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes=[VendorJWTAuthentication]
    def get(self, request, dish_id):
        reviews = DishReview.objects.filter(dish_id=dish_id)
        serializer = DishReviewSerializer(reviews, many=True)
        return Response(serializer.data)

class DishReviewListView(generics.ListAPIView):

    queryset = DishReview.objects.all()
    serializer_class = DishReviewSerializer
    permission_classes = [IsAuthenticated]  # Optional: Use this to restrict access
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Filtering fields
    filterset_fields = ['dish__id', 'user__id', 'rating']

    # Searchable fields
    search_fields = ['review', 'dish__name', 'user__username']

    # Ordering options
    ordering_fields = ['created_at', 'rating', 'dish__name']
    ordering = ['-created_at']  # Default ordering