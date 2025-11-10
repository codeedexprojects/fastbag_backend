from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from groceryproducts.models import *
from rest_framework.permissions import IsAuthenticated
from groceryproducts.serializers import *
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from vendors.authentication import VendorJWTAuthentication

class Grocery_WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        wishlist_items = Grocery_Wishlist.objects.filter(user=user)
        serializer = GroceryWishlistSerializer(wishlist_items, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({'error': 'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = GroceryProducts.objects.get(id=product_id)
        except GroceryProducts.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        if Grocery_Wishlist.objects.filter(user=user, product=product).exists():
            return Response({'message': 'Product is already in the wishlist'}, status=status.HTTP_200_OK)

        wishlist_item = Grocery_Wishlist.objects.create(user=user, product=product)
        serializer = GroceryWishlistSerializer(wishlist_item, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        user = request.user
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({'error': 'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = GroceryProducts.objects.get(id=product_id)
        except GroceryProducts.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        wishlist_item = Grocery_Wishlist.objects.filter(user=user, product=product).first()
        if not wishlist_item:
            return Response({'error': 'Product not in wishlist'}, status=status.HTTP_404_NOT_FOUND)

        wishlist_item.delete()
        return Response({'message': 'Product removed from wishlist'}, status=status.HTTP_200_OK)

class AddGroceryProductReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GroceryProductReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ListGroceryProductReviewsView(APIView):
    authentication_classes = [VendorJWTAuthentication]

    def get(self, request, product_id):
        reviews = GroceryProductReview.objects.filter(product_id=product_id)
        serializer = GroceryProductReviewSerializer(reviews, many=True)
        return Response(serializer.data)

class DeleteGroceryProductReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, review_id):
        try:
            review = GroceryProductReview.objects.get(id=review_id, user=request.user)
        except GroceryProductReview.DoesNotExist:
            return Response(
                {"error": "Review not found or you do not have permission to delete it."},
                status=status.HTTP_404_NOT_FOUND,
            )
        review.delete()
        return Response({"message": "Review deleted successfully."}, status=status.HTTP_200_OK)

class GroceryProductReviewListView(generics.ListAPIView):
    """
    List all reviews for grocery products.
    """
    queryset = GroceryProductReview.objects.all()
    serializer_class = GroceryProductReviewSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['product__id', 'user__id', 'rating']  # Filter by product, user, or rating
    search_fields = ['review', 'product__name', 'user__username']  # Search by review content, product name, or username
    ordering_fields = ['created_at', 'rating']  # Order by creation date or rating
    ordering = ['-created_at']