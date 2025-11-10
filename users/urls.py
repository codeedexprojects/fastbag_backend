from django.urls import path
from users.views.userdetails import *
from users.views.usersideviews import *
from rest_framework_simplejwt.views import TokenRefreshView
from users.views.userswishlists import *
from users.views.subadmin import *
from users.views.notification_user import *
from users.views.coupons import *


urlpatterns = [
    #admin
    path('admin/login/', AdminLoginView.as_view(), name='admin-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    #user login
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    #user address
    path('addresses/', AddressView.as_view(), name='address-list'),
    #address update
    path('address/<int:pk>/update/', AddressUpdateView.as_view(), name='address-update'),
    #user detail update
    path('user/update/', UserUpdateView.as_view(), name='user-update'),
    #all product view from user side
    path('unified-products/', UnifiedProductListView.as_view({'get': 'list'})),
    #all category/subcategory
    path('unified-categories/', UnifiedCategoryListView.as_view(), name='unified-category-list'),
    #product by category
    path('products/category/<int:category_id>/', ProductsByCategoryView.as_view(), name='products-by-category'),
    #user details admin
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    #user info
    path('users/info/<int:pk>/', UserInfo.as_view(), name='user-detail'),
    #user list admin
    path('users/', UserListView.as_view(), name='user-list'),
    #wishlist by user - admin
    path('admin/users/wishlists/<int:user_id>/', UserWishlistDetailView.as_view(), name='user-wishlist-detail'),
    # manage reported products-admin
    path('reports/', ReportListView.as_view(), name='report-list'),
    #view reviews by user
    path('reviews/', ReviewListView.as_view(), name='review-list'),
    #sub-admin
    path('create-staff/', CreateStaffView.as_view(), name='create_staff'),
    path('staff/', StaffListView.as_view(), name='staff-list'),
    path('staff/<str:mobile_number>/', StaffDetailView.as_view(), name='staff-detail'),
    path('staff/<str:mobile_number>/update/', StaffUpdateView.as_view(), name='staff-update'),
    path('staff/<str:mobile_number>/delete/', StaffDeleteView.as_view(), name='staff-delete'),
    #notifiaction - registration
    path('admin-notifications/',
         AdminNotificationViewSet.as_view({'get': 'list','post': 'create'}),name='admin-notification-list'),
    # Unread count
    path('admin-notifications/unread_count/',
    AdminNotificationViewSet.as_view({'get': 'unread_count'}),name='admin-notification-unread-count'),
    # Mark all read
    path('admin-notifications/mark_all_read/',
         AdminNotificationViewSet.as_view({'post': 'mark_all_read'}),
         name='admin-notification-mark-all-read'),
    # Notification detail
    path('admin-notifications/<int:pk>/',
         AdminNotificationViewSet.as_view({
             'get': 'retrieve',
             'put': 'update',
             'patch': 'partial_update',
             'delete': 'destroy'
         }),
         name='admin-notification-detail'),
    # Mark single read
    path('admin-notifications/<int:pk>/mark_read/',
         AdminNotificationViewSet.as_view({'post': 'mark_read'}),
         name='admin-notification-mark-read'),
    #subcat by cat id
    path('subcategories/<int:category_id>/', SubcategoriesByCategoryView.as_view(), name='subcategories-by-category'),
    #product by sub category
    path('subcategory-products/<str:subcategory_type>/<int:subcategory_id>/', ProductsBySubcategoryView.as_view()),
    #sub cat by vendors
    path('vendor-subcategories/<int:vendor_id>/', SubCategoriesByVendorAPIView.as_view(), name='subcategories-by-vendor'),
    #fav vendor
    path('favourite-vendor/add/', AddFavoriteVendorView.as_view(), name='add-favorite-vendor'),
    path('favourite-vendor/remove/<int:vendor_id>/', RemoveFavoriteVendorView.as_view(), name='remove-favorite-vendor'),
    path('vendors/favourites/', ListFavoriteVendorsView.as_view(), name='list-favorite-vendors'),
    #big buy
    path('big-buy-order/', BigBuyOrderCreateView.as_view(), name='big-buy-order-create'),
    path('big-buy-orders/', BigBuyOrderListView.as_view(), name='big-buy-order-list'),#list
    path('big-buy-order/<int:pk>/', BigBuyOrderDetailView.as_view(), name='big-buy-order-detail'),#detail
    #update
    # path('big-buy-order/<int:pk>/edit/', BigBuyOrderUpdateView.as_view(), name='big-buy-order-edit'),
    #admin
    path('admin/big-buy-orders/', AdminBigBuyOrderListView.as_view(), name='admin-big-buy-order-list'),
    path('admin/big-buy-order/<int:pk>/', AdminBigBuyOrderDetailView.as_view(), name='admin-big-buy-order-detail'),
    path('admin/big-buy-order/<int:pk>/update/', AdminBigBuyOrderUpdateView.as_view(), name='admin-big-buy-order-update'),
    path('orders/bigbuy/<int:order_id>/cancel/', CancelBigBuyOrderView.as_view(), name='cancel-bigbuy-order'),#cancel
    #coupons
    path('coupons/', CouponCreateView.as_view(), name='coupon-list-create'),
    path('coupons/<int:pk>/', CouponRetrieveAPIView.as_view(), name='coupon-detail'),
    path('coupons/view/', CouponListView.as_view(), name='vendor-coupon-list'),
    #set primary address
    path('set-primary/<int:address_id>/', SetPrimaryAddressView.as_view(), name='set-primary-address'),
     # user location
    path('user-location/create/', UserLocationCreateView.as_view(), name='user-location-create'),
    path('user-location/update/<int:pk>/', UserLocationUpdateView.as_view(), name='user-location-update'),
    path('staff-login/', StaffLoginView.as_view(), name='staff-login'),
    path('admin/users/<int:user_id>/addresses/<int:address_id>/',AdminUserAddressUpdateView.as_view(),name='admin-user-address-update'),
    path('wishlist/', UserWishlistView.as_view(), name='wishlist-list'),
    path('view-coupon/', CouponListForUsers.as_view(), name='coupon-list-users'),
    path('coupons/vendor/', VendorCouponListView.as_view(), name='vendor-coupon-list'),


]