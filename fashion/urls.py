from django.urls import path
from fashion.views.clothcategories import *
from fashion.views.clothproducts import *
from fashion.views.coupons import *
from fashion.views.clothwishlist import *

urlpatterns = [
    # Categories
    path('categories/', ClothingCategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', ClothingCategoryDetailView.as_view(), name='category-detail'),
    #clothing sub-cat
    path('clothing-subcategories/', ClothingSubCategoryListCreateView.as_view(), name='clothing-subcategory-list-create'),
    path('clothing-subcategories/<int:pk>/', ClothingSubCategoryDetailView.as_view(), name='clothing-subcategory-detail'),
    # Clothing
    path('clothing/', ClothingListCreateView.as_view(), name='clothing-list-create'),
    path('clothing/list/admin/', ClothingListViewAdmin.as_view(), name='clothing-list-admin'),
    path('clothing/admin/', ClothingListCreateViewAdmin.as_view(), name='clothing-list-create-admin'),
    path('clothing/details/<int:pk>/', ClothingDetailView.as_view(), name='clothing-detail'),
    path('clothing/<int:pk>/', ClothingDetailViewAdmin.as_view(), name='clothing-detail'),
    path('clothing/list/user/', ClothingListViewUser.as_view(), name='clothing-list-user'),
    path('clothing-user/<int:pk>/', ClothingDetailViewUser.as_view(), name='clothing-detail'),
    # Clothing Images
    path('clothing/images/admin/', ClothingImageListCreateView.as_view(), name='clothing-image-list-create'), #admin
    path('clothing-images/admin/<int:pk>/', ClothingImageRetrieveUpdateDestroyView.as_view(), name='clothing-image-detail'),#admin
    path('clothing/images-add/', ClothingImageListCreateViewVendor.as_view(), name='clothing-image-list-create-vendor'),
    #Delete Images
    path('clothing/images/<int:image_id>/delete/', ClothingImageDeleteView.as_view(), name='clothing-image-delete'),
    #update image
    path('clothing/images/<int:image_id>/update/', ClothingImageUpdateView.as_view(), name='clothing-image-update'),
    #color
    path('colors/', ColorListView.as_view(), name='color-list'),
    path('colors/create/', ColorCreateView.as_view(), name='color-create'),
    path('colors/detail/<int:pk>/', ColorDetailView.as_view(), name='color-details'),
    #product filters
    path('products/category/<int:category_id>/vendor/<int:vendor_id>/', ProductsByCategoryView.as_view(), name='products-by-category'),
    path('products/subcategory/<int:subcategory_id>/vendor/<int:vendor_id>/', ProductsBySubCategoryView.as_view(), name='products-by-subcategory'),
    #product by cat and sub cat
    path('products/category/<int:category_id>/subcategory/<int:subcategory_id>/vendor/<int:vendor_id>/',
     ProductsByCategorySubCategoryView.as_view(), name='products-by-category-subcategory-vendor'),
    # search
    path('fashion/search/', SearchView.as_view(), name='search'),
    #create coupons
    path('coupons/', CouponListCreateView.as_view(), name='coupon-list-create'),\
    #update
    path('coupons/update/<int:pk>/', CouponUpdateView.as_view(), name='coupon-update'),
    #coupons
    path('apply-coupon/', ApplyCouponView.as_view(), name='apply-coupon'),
    #coupon usage
    path('coupon-usages/', CouponUsageListView.as_view(), name='coupon-usage-list'),
    #wishlist
    path('wishlist/', WishlistListCreateView.as_view(), name='wishlist-list-create'),
    path('wishlist/<int:cloth_id>/', WishlistDeleteView.as_view(), name='wishlist-delete'),
    #reviews
    path('reviews/', FashionReviewListCreateView.as_view(), name='fashion-review-list-create'),
    path('reviews/<int:pk>/', FashionReviewDeleteView.as_view(), name='fashion-review-delete'),
    path('fashion/reviews/<int:cloth_id>/', ListFashionProductReviewsView.as_view(), name='list-dish-reviews'),
    path('reviews/cloth/<int:cloth_id>/', FashionReviewByClothIDView.as_view(), name='reviews-by-cloth'),
    #report
    path('reports/', FashionReportListCreateView.as_view(), name='fashion-report-list-create'),
    path('reports/<int:pk>/', FashionReportUpdateView.as_view(), name='fashion-report-update'),#admin
    path('reports/delete/<int:pk>/', FashionReportDeleteView.as_view(), name='fashion-report-delete'),
    #count
    path('clothing-products/count/', ClothingProductCountView.as_view(), name='clothing-product-count'),
    #sub cat by cat
    path('subcategories/by-category/<int:category_id>/', ClothingSubCategoryListByCategory.as_view(), name='subcategory-by-category'),
    path("fashion/offer-products/", OfferProductsViewfashion.as_view(), name="offer-products"),


]
