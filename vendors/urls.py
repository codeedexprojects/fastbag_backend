from django.urls import path
from .views import *


category_list = CategoryViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

category_detail = CategoryViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

category_lists = CategoryView.as_view({
    'get': 'list',
})

urlpatterns = [
    #store types (admin)
    path('store-types/', StoreTypeListCreateView.as_view(), name='store-type-list-create'),
    path('store-types/<int:pk>/', StoreDetailView.as_view(), name='store-type-list-detail'),
    path('store-list/', StoreTypeListView.as_view(), name='store-type-list'),
    #vendors
    path('vendors/', VendorListCreateView.as_view(), name='vendor-list-create'),
    path('vendors/<int:pk>/', VendorDetailView.as_view(), name='vendor-detail'),
    path('vendors-admin-view/<int:pk>/', VendorDetailViewAdmin.as_view(), name='vendor-detail-admin'),
    path('vendors-home/', VendorListView.as_view(), name='vendor-list'),
    path('vendors-view/', VendorListViewAdmin.as_view(), name='vendor-list-admin'),
    #approve changes
    path('vendors/pending/<int:pk>/', VendorPendingDetailView.as_view(), name='vendor-pending-detail'),
    path('approve-changes/<int:pk>/', ApproveVendorUpdateView.as_view(), name='approve-vendor-changes'),
    #accept reject vendors - (admin)
    path('vendor-accept-reject/<int:pk>/', VendorAdminAcceptReject.as_view(), name='vendor-admin-update'),
    #enable / disable vendor - (admin)
    path('vendor-enable-disable/<int:pk>/',VendorEnableDisableView.as_view(), name='vendor-admin-enable-disable') ,
    #filter accpt - reject vendors
    path('vendors/filter/', VendorFilterListView.as_view(), name='vendor-filter-list'),
    #For filter by store type
    path('stores/by-type/<int:store_type_id>/', StoresByTypeView.as_view(), name='stores-by-type'),
    #vendor filter by category name
    # path('vendors/by-category/<str:category_name>/', VendorByCategoryListView.as_view(), name='vendors-by-category'),
    #login
    path('vendor/login/', VendorLoginView.as_view(), name='vendor-login'),
    path('vendor/verify-otp/', VendorOTPVerifyView.as_view(), name='vendor-verify-otp'),
    path('vendor/token/refresh/', VendorTokenRefreshView.as_view(), name='vendor-token-refresh'),
    path('vendor/approval-status/<int:id>/', VendorApprovalStatusView.as_view(), name='vendor-approval-status'),
    #forgot mail
    path('forgot-email/send-otp/', ForgotEmailSendOTPView.as_view(), name='forgot-email-send-otp'),
    path('forgot-email/verify-otp/', ForgotEmailVerifyOTPView.as_view(), name='forgot-email-verify-otp'),
    #category
    path('categories/', category_list, name='category-list'),
    path('categories/<int:pk>/', category_detail, name='category-detail'),
    path('categories/view/', category_lists, name='category-list-view'),
    path('subcategories/admin/', SubCategoryListView.as_view(), name='subcategories-list'),
    path('products/vendor/<int:vendor_id>/', VendorProductListView.as_view(), name='products-by-vendors'),#admin
    #fav vendors
    path('vendor/favourite/<int:pk>/', VendorFavouriteView.as_view(), name='vendor-favourite'),
    path('user/favourite-vendors/', UserFavouriteVendorsView.as_view(), name='user-favourite-vendors'),
    #product count by vendors
    path('dish-count/<int:vendor_id>/', VendorProductsCountView.as_view(), name='single-vendor-dish-count'),
    #filter categories by store type
    path('categories/filter/', CategoryListView.as_view(), name='category-list'),
    #available product count
    path('available-product-count/<int:vendor_id>/', VendorAvailableProductsCountView.as_view(), name='vendor-available-product-count'),
    #out stock product count
    path('out-of-stock-count/<int:vendor_id>/', VendorOutOfStockDetailView.as_view(), name='vendor-out-of-stock-count'),
    #dashboard analytics
    path('analytics/<int:vendor_id>/', VendorAnalyticsView.as_view(), name='vendor-analytics'),
    #category search
    path('categories/search/', CategorySearchAPIView.as_view(), name='category-search'),
    #sub cat
    path('admin/subcategories/', SubCategoryListView.as_view(), name='subcategory-list'),
    path('admin/subcategories/create/', SubCategoryCreateView.as_view(), name='subcategory-create'),
    path('admin/subcategories/<int:pk>/', SubCategoryUpdateDeleteView.as_view(), name='subcategory-update-delete'),
    #sub category request / list
    path('request-subcategory/', SubCategoryRequestCreateView.as_view(), name='request-subcategory'),
    path('admin/subcategory-requests/', SubCategoryRequestListView.as_view(), name='admin-subcategory-requests'),
    path('vendor/subcategory-requests/', VendorSubCategoryRequestListView.as_view(), name='vendor-subcategory-requests'),
    path('admin/approve-subcategory/<int:request_id>/', ApproveSubCategoryRequestView.as_view(), name='approve-subcategory'),
    #sub cat list by category
    path('subcategories/by-category/<int:category_id>/', SubCategoryListByCategory.as_view(), name='subcategory-by-category'),
    #vendor search
    path('vendors/search/', VendorSearchView.as_view(), name='vendor-search'),
    #nearby vendors
    path('vendors/nearby/', NearbyVendorsAPIView.as_view(), name='nearby-vendors'),
    path('vendors/nearby-categories/', NearbyVendorCategoriesOnlyAPIView.as_view(), name='nearby-vendor-categories'),
    path('analytics/vendor-orders/<int:vendor_id>/', VendorOrderAnalyticsView.as_view(), name='vendor-order-analytics'),
    #carousel
    path('app-carousel/', AppCarouselListCreateView.as_view(), name='app-carousel-list-create'),
    path('ads-carousel/by-loc/', AdsCarouselListCreateView.as_view(), name='app-carousel-list-create'),
    path("ads-carousel/<int:id>/", AdsCarouselDetailView.as_view(), name="ads-carousel-detail"),
    path('app-carousel/user/', AppCarouselListViewUser.as_view(), name='app-carousel-list-view'),
    path('app-carousel/<int:pk>/', AppCarouselDetailView.as_view(), name='app-carousel-detail'),
    path('app-carousel/user-by-loc/', AdsCarouselListViewUserLoc.as_view(), name='app-carousel-list-view'),
    path('vendors/category/<int:category_id>/', VendorByCategoryLocationView.as_view(), name='vendors-by-category-location'),

    path("vendor-videos/", VendorVideoListCreateView.as_view(), name="vendorvideo-list-create"),
    path("vendor-videos-admin/", VendorVideoListViewAdmin.as_view(), name="vendorvideo-list-admin"),
    path("vendor-videoadmin/<int:pk>/", VendorVideoDetailViewAdmin.as_view(), name="vendorvideo-detail-admin"),
    path("vendor-videos/<int:pk>/", VendorVideoDetailView.as_view(), name="vendorvideo-detail"),
    path("vendor/video-list/", VendorVideoListView.as_view(), name="vendor-video-list"),

    path("vendors-products/<int:vendor_id>/", VendorProductsView.as_view(), name="vendor-products"),
    path("popular-restaurent/",NearbyRestaurantsAPIView.as_view(),name="nearby-restaurants",),
    #commission
    path("admin/vendor-commissions/", VendorCommissionAPIView.as_view(), name="vendor-commissions"),
    path("subcategory-requests/", SubCategoryRequestListView.as_view(), name="subcategory-request-list"),


]