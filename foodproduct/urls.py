from django.urls import path
from foodproduct.views.foodcategories import *
from foodproduct.views.foodproducts import *
from foodproduct.views.foodwishlist import *
from foodproduct.views.foodbanner import *
from foodproduct.views.foodcoupon import *

urlpatterns = [

    path('dishes/', DishCreateView.as_view(), name='Food-dish-create'),
    path('dishes/admin/', DishCreateViewAdmin.as_view(), name='Food-dish-create'), #admin
    path('dishes/admin/<int:id>/', DishDetailViewAdmin.as_view(), name='Food-dish-create'), #admin
    path('dishes/list/', DishListView.as_view(), name='Food-dish-list'),
    path('dishes/list/admin/', DishListViewAdmin.as_view(), name='Food-dish-list-admin'),#admin
    path('dishes/<int:id>/', DishDetailView.as_view(), name='Food-dish-detail'),
    path('dishes-user/<int:id>/', DishDetailViewUser.as_view(), name='Food-dish-detail'),
    # Dish images
    path('Dish/images-add/', FoodImageListCreateViewVendor.as_view(), name='dish-image-list-create-vendor'),
    #delete images
    path('food/images/<int:image_id>/delete/', FoodImageDeleteView.as_view(), name='food-image-delete'),
    #update image
    path('food/images/<int:image_id>/update/', foodImageUpdateView.as_view(), name='food-image-update'),
    #single product
    path('single-dish/<int:pk>/', SingleDishDetailView.as_view(), name='dish-detail'),
    path('addons/create/', DishAddOnCreateView.as_view(), name='Food-addon-create'),
    path('addons/', DishAddOnListView.as_view(), name='Food-addon-list'),
    #offer product and popular product,
    path('Dish/offer/', DishOfferProductListView.as_view(), name='offer-products'),
    path('Dish/popular/', DishPopularProductListView.as_view(), name='popular-products'),
     #product search
    path('Dish/search/', DishSearchFilterView.as_view(), name='product-search'),
    #dish stats - vendor/admin
    path('dish-stats/', DishStatsView.as_view(), name='dish-stats'),
    # #Category URLs
    path('food-categories/', FoodCategoryListCreateView.as_view(), name='category-list-create'),
    path('food-categories/view/', FoodCategoryListView.as_view(), name='category-list-view'),
    path('food-categories/<int:pk>/', FoodCategoryDetailView.as_view(), name='category-detail'),
    # # SubCategory URLs
    path('subcategories/', FoodSubCategoryListCreateView.as_view(), name='subcategory-list-create'),
    path('subcategories/view/', FoodSubCategoryListView.as_view(), name='subcategory-list-view'),
    path('subcategories/view/admin/', FoodSubCategoryListViewAdmin.as_view(), name='subcategory-list-view-admin'),
    path('subcategories/<int:pk>/', FoodSubCategoryDetailView.as_view(), name='subcategory-detail'),
    #food categories by vendor - search
    path('vendors-by-category/', VendorByCategoryView.as_view(), name='vendors-by-category'),
    #sub categories by vendor search
    path('vendors-by-sub-category/', VendorBySubCategoryView.as_view(), name='vendors-by-sub-category'),
    #all vendor categories
    path('vendor-categories/<int:vendor_id>/', VendorCategoryListView.as_view(), name='vendor-category-list'),
    #all vendor sub-categories
    path('vendor-sub-categories/<int:vendor_id>/', VendorFoodSubCategoryListView.as_view(), name='vendor-sub-category-list'),
    #all products list by vendor
    path('vendors/products/<int:vendor_id>/', VendorProductListView.as_view(), name='vendor-product-list'),
    #all products by cat sub-cat
    path('food/dishes/<int:vendor_id>/<int:category_id>/<int:subcategory_id>/', DishFilterListView.as_view(), name='filtered-dishes-by-ids'),
    #vendors by category
    path('vendors-by-category/<int:category_id>/', VendorsByCategoryView.as_view(), name='vendors-by-category'),
    #wish list
    path('wishlist/', WishlistView.as_view(), name='wishlist-list'),  # To view the wishlist
    path('wishlist/add/', WishlistView.as_view(), name='wishlist-add'),  # To add a product to the wishlist
    path('wishlist/remove/', WishlistView.as_view(), name='wishlist-remove'),  # To remove a product from the wishlist
    #review and ratings
    path('dishes/reviews/', DishReviewCreateView.as_view(), name='create-dish-review'),
    path('dishes/reviews/<int:review_id>/', DishReviewDeleteView.as_view(), name='delete-dish-review'),
    path('dish/reviews/<int:dish_id>/', ListFoodProductReviewsView.as_view(), name='list-dish-reviews'),
    #review list - food
    path('dish/review-list/',DishReviewListView.as_view(),name='all-review-list'),
    #report product
    path('dishes/report/', ReportDishView.as_view(), name='report-dish'),
    #report list
    path('dishes/reports/list/', ReportedDishListView.as_view(), name='reported-dishes'),
    #edit report detail
    path('dishes/reports/<int:pk>/resolve/', ResolveDishReportView.as_view(), name='resolve-dish-report'),
    #foodbanner
    path('create-banner/food/', VendorBannerFoodProductsCreateAPIView.as_view(), name='create-banner'),#create
    #update delete get
    path('food-banner/<int:pk>/', VendorBannerFoodProductsRetrieveUpdateDestroyAPIView.as_view(), name='banner-detail'),
    #list
    path('banners/list/', VendorBannerFoodProductsListView.as_view(), name='banners-list'),
    #create coupons
    path('food-coupons/', FoodCouponListCreateView.as_view(), name='coupon-list-create'),\
    #update
    path('food-coupons/update/<int:pk>/', FoodCouponUpdateView.as_view(), name='coupon-update'),
    #coupons
    path('apply-food-coupon/', FoodApplyCouponView.as_view(), name='apply-coupon'),
    #coupon usage
    path('food-coupon-usages/', FoodCouponUsageListView.as_view(), name='coupon-usage-list'),
    #sub cat by category
    path('subcategories/by-category/<int:category_id>/', FoodSubCategoryListByCategory.as_view(), name='subcategory-by-category'),
    #products by subcategory
    path('products/subcategory/<int:subcategory_id>/vendor/<int:vendor_id>/', ProductsBySubCategoryView.as_view(), name='products-by-subcategory-food'),
]