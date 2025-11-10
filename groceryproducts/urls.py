from django.urls import path
from groceryproducts.views.grocerycategories import *
from groceryproducts.views.groceryproducts import *
from groceryproducts.views.grocerywishlist import *
from groceryproducts.views.grocerycoupons import *


urlpatterns = [

#categories
    path('gro-categories/', GroceryCategoryListView.as_view(), name='Grocery-category-list'),
    path('gro-categories/list/', Gro_CategoryListView.as_view(), name='Grocery-category-list-user'),
    path('gro-categories/<int:pk>/', GroceryCategoryDetailView.as_view(), name='Grocery-category-detail'),
#sub categories
    path('gro-Subcategories/', GrocerySubCategoryListView.as_view(), name='Grocery-sub-category-list'),
    path('gro-Subcategories/list/', Gro_SubCategoryListView.as_view(), name='Grocery-sub-category-list-view'),
    path('gro-Subcategories/list/admin/', GrocerySubCategoryListViewAdmin.as_view(), name='Grocery-sub-category-list-view-admin'),
    path('gro-Subcategories/<int:pk>/', GrocerySubCategoryDetailView.as_view(), name='Grocery-sub-category-detail'),
    #product images
    path('Dish/images-add/', GroceryImageListCreateViewVendor.as_view(), name='dish-image-list-create-vendor'),
#delete images
    path('food/images/<int:image_id>/delete/', GroceryImageDeleteView.as_view(), name='food-image-delete'),
    #update image
    path('food/images/<int:image_id>/update/', GroceryImageUpdateView.as_view(), name='food-image-update'),
#products
    path('products/', GroceryProductCreateView.as_view(), name='Grocery-product-list'),
    path('products/admin/', GroceryProductCreateViewAdmin.as_view(), name='Grocery-product-add'), #admin
    path('products/list/', groceryproductlistviewadmin.as_view(), name='product-list'),
#prod detail users
    path('products-user/<int:pk>/', GroceryProductDetailViewUser.as_view(), name='product-detail'),
#for complete product details
    path('products/<int:pk>/', GroceryProductDetailView.as_view(), name='product-detail'),
    path('products/admin/<int:pk>/', GroceryProductDetailViewAdmin.as_view(), name='product-detail-admin'),
#product complete list
    path('grocery-products/list/', GroceryProductListView.as_view(), name='Grocery-product-list'),
#offer product and popular product
    path('products/offer/', GroceryOfferProductListView.as_view(), name='offer-products'),
    path('products/popular/', GroceryPopularProductListView.as_view(), name='popular-products'),
#product search
    path('products/search/', ProductSearchFilterView.as_view(), name='product-search'),
#wishlist
    path('wishlist/', Grocery_WishlistView.as_view(), name='wishlist-list'),  # To view the wishlist
    path('wishlist/add/', Grocery_WishlistView.as_view(), name='wishlist-add'),  # To add a product to the wishlist
    path('wishlist/remove/', Grocery_WishlistView.as_view(), name='wishlist-remove'),  # To remove a product from the wishlist
#reviews and ratings
    path('products/reviews/<int:product_id>/', ListGroceryProductReviewsView.as_view(), name='list-product-reviews'),
    path('product/reviews/', AddGroceryProductReviewView.as_view(), name='add-product-review'),
    path('reviews/<int:review_id>/', DeleteGroceryProductReviewView.as_view(), name='delete-product-review'),
#review listing by users - grocery
    path('grocery/reviews/', GroceryProductReviewListView.as_view(), name='grocery-product-reviews'),
#product stats
    path('product-stats/', GroceryProductStatsView.as_view(), name='product-stats'),
#vendors by category list
    path('grocery-categories/', GroVendorByCategoryView.as_view(), name='enabled-categories'),
#vendors by sub-category list
    path('grocery-sub-categories/', GroVendorBySubcategoryView.as_view(), name='enabled-sub-categories'),
#product list by vendors
    path('grocery/vendors/products/<int:vendor_id>/', GroceryProductListView.as_view(), name='vendor-product-list'),
#allproducts list
    path('all-products/list/', Allgroceryproducts.as_view(), name='product-list'),
#vendor list by categories
    path('vendors-by-grocery-category/<int:category_id>/', VendorsByGroceryCategoryView.as_view(), name='vendors-by-grocery-category'),
#report product
    path('grocery-product/report/', ReportGroceryProductView.as_view(), name='report-grocery-product'),
#reported product list
    path('reported-grocery-products/', ReportedGroceryProductListView.as_view(), name='reported-grocery-products'),
#edit resolved
    path('resolve-grocery-product-report/<int:pk>/', ResolveGroceryProductReportView.as_view(), name='resolve-grocery-product-report'),
#create coupons
    path('grocery-coupons/', GroceryCouponListCreateView.as_view(), name='coupon-list-create'),
#update
    path('grocery-coupons/update/<int:pk>/', GroceryCouponUpdateView.as_view(), name='coupon-update'),
#coupons
    path('grocery-coupon-Apply/', GroceryApplyCouponView.as_view(), name='apply-coupon'),
#coupon usage
    path('grocery-coupon-usages/', GroceryCouponUsageListView.as_view(), name='coupon-usage-list'),
#products by sub cat and vendor
    path('products/<int:vendor_id>/<int:sub_category_id>/', GroceryProductsBySubcategoryVendorView.as_view(), name='products-by-vendor-subcategory'),
#products by subcategory
    path('products/subcategory/<int:subcategory_id>/vendor/<int:vendor_id>/', ProductsBySubCategoryView.as_view(), name='products-by-subcategory-grocery'),
#sub cat by category
    path('subcategories/by-category/<int:category_id>/', GrocerySubCategoryListByCategory.as_view(), name='subcategory-by-category'),




]