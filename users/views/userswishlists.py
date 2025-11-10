from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import NotFound
from django.contrib.auth import get_user_model
from groceryproducts.serializers import *
from fashion.serializers import *
from foodproduct.serializers import *
from users.serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from vendors.serializers import VendorHomePageSerializer

User = get_user_model()

class UserWishlistDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, user_id, *args, **kwargs):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound("User not found.")

        grocery_wishlist = Grocery_Wishlist.objects.filter(user=user)
        fashion_wishlist = FashionWishlist.objects.filter(user=user)
        wishlist = Wishlist.objects.filter(user=user)

        total_wishlist_count = (
            grocery_wishlist.count() +
            fashion_wishlist.count() +
            wishlist.count()
        )
        data = {
            "total_wishlist_count": total_wishlist_count,
            "user_id": user.id,
            "mobile_number": user.mobile_number,
            "name": user.name,
            "email": user.email,
            "grocery_wishlist": GroceryWishlistSerializer(grocery_wishlist, many=True).data,
            "fashion_wishlist": FashionWishlistSerializer(fashion_wishlist, many=True).data,
            "food_wishlist": WishlistSerializer(wishlist, many=True).data,
        }

        return Response(data)

class ReportListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        product_type = request.query_params.get('product_type', None)
        is_resolved = request.query_params.get('is_resolved', None)

        grocery_reports = GroceryProductReport.objects.all()
        dish_reports = DishReport.objects.all()
        fashion_reports = FashionReport.objects.all()

        if is_resolved is not None:
            grocery_reports = grocery_reports.filter(is_resolved=is_resolved)
            dish_reports = dish_reports.filter(is_resolved=is_resolved)
            fashion_reports = fashion_reports.filter(is_resolved=is_resolved)

        if product_type == 'grocery':
            serializer = GroceryProductReportSerializer(grocery_reports, many=True)
            return Response({"grocery_reports": serializer.data})
        elif product_type == 'dish':
            serializer = DishReportSerializer(dish_reports, many=True)
            return Response({"dish_reports": serializer.data})
        elif product_type == 'fashion':
            serializer = FashionReportSerializer(fashion_reports, many=True)
            return Response({"fashion_reports": serializer.data})

        grocery_serializer = GroceryProductReportSerializer(grocery_reports, many=True)
        dish_serializer = DishReportSerializer(dish_reports, many=True)
        fashion_serializer = FashionReportSerializer(fashion_reports, many=True)

        data = {
            "grocery_reports": grocery_serializer.data,
            "dish_reports": dish_serializer.data,
            "fashion_reports": fashion_serializer.data
        }
        return Response(data)

class ReviewListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Query parameters
        review_type = request.query_params.get('review_type', None)

        # Initialize response data
        data = {}

        # Fetch and serialize reviews for specific types or all
        if review_type == 'dish':
            reviews = DishReview.objects.all()
            serializer = DishReviewSerializer(reviews, many=True)
            data['dish_reviews'] = serializer.data
        elif review_type == 'grocery':
            reviews = GroceryProductReview.objects.all()
            serializer = GroceryProductReviewSerializer(reviews, many=True)
            data['grocery_reviews'] = serializer.data
        elif review_type == 'fashion':
            reviews = FashionReview.objects.all()
            serializer = FashionReviewSerializer(reviews, many=True)
            data['fashion_reviews'] = serializer.data
        else:
            # Fetch all reviews
            dish_reviews = DishReview.objects.all()
            grocery_reviews = GroceryProductReview.objects.all()
            fashion_reviews = FashionReview.objects.all()

            data['dish_reviews'] = DishReviewSerializer(dish_reviews, many=True).data
            data['grocery_reviews'] = GroceryProductReviewSerializer(grocery_reviews, many=True).data
            data['fashion_reviews'] = FashionReviewSerializer(fashion_reviews, many=True).data

        return Response(data)


class AddFavoriteVendorView(generics.CreateAPIView):
    serializer_class = FavoriteVendorSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        vendor = serializer.validated_data['vendor']

        if FavoriteVendor.objects.filter(user=user, vendor=vendor).exists():
            raise serializers.ValidationError({"error": "Already in favorites."})

        serializer.save(user=user)


class RemoveFavoriteVendorView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'vendor_id'

    def delete(self, request, *args, **kwargs):
        vendor_id = self.kwargs.get(self.lookup_url_kwarg)
        user = request.user
        try:
            favorite = FavoriteVendor.objects.get(user=user, vendor_id=vendor_id)
            favorite.delete()
            return Response({"status": True, "message": "Vendor removed from favourites."}, status=200)
        except FavoriteVendor.DoesNotExist:
            return Response({"status": False, "message": "Vendor not found in your favourites."}, status=404)


class ListFavoriteVendorsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteVendorSerializer
    pagination_class = None


    def get_queryset(self):
        return FavoriteVendor.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context

from rest_framework import status

class UserWishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Fetch wishlists
        grocery_items = Grocery_Wishlist.objects.filter(user=user)
        dish_items = Wishlist.objects.filter(user=user)
        fashion_items = FashionWishlist.objects.filter(user=user)

        # Serialize
        grocery_data = GroceryWishlistSerializer(grocery_items, many=True).data
        dish_data = WishlistSerializer(dish_items, many=True).data
        fashion_data = FashionWishlistSerializer(fashion_items, many=True).data

        # Combine
        data = {
            "grocery": grocery_data,
            "dish": dish_data,
            "fashion": fashion_data
        }

        return Response(data, status=status.HTTP_200_OK)


