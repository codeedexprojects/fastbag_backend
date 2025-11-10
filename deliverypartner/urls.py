from django.urls import path
from deliverypartner.views import *


urlpatterns =[

    path('delivery_boys/', DeliveryBoyListCreateView.as_view(), name='delivery_boy_list_create'), #create
    path('delivery_boys/<int:pk>/', DeliveryBoyDetailView.as_view(), name='delivery_boy_detail'), #delivery boy details admin
    path('deliveryboy/<int:delivery_boy_id>/', DeliveryBoyDetailViewUser.as_view(), name='deliveryboy-detail'), #edit detail

    #login
    path('request-otp/', RequestOTPView.as_view(), name='request_otp'),
    path('login-with-otp/', LoginWithOTPView.as_view(), name='login_with_otp'),

    #assing order

    path('orderassign/', OrderAssignCreateView.as_view(), name='order-assign-create'),
    path('deliveryboy/<int:delivery_boy_id>/assigned-orders/', DeliveryBoyAssignedOrdersView.as_view(), name='assigned-orders-for-deliveryboy'),
    path('orderassign/<int:pk>/status/', OrderAssignStatusUpdateView.as_view(), name='update-order-assign-status'),
    path('delivery/orderassign/filter/', OrderAssignStatusFilterView.as_view(), name='orderassign-status-filter'),#filter by status
    #assign order - updated
    path('notifications/<int:pk>/mark-read/', MarkNotificationAsReadView.as_view(), name='mark-notification-read'),
    path('accept_order/<int:delivery_boy_id>/<int:order_id>/', AcceptOrderView.as_view(), name='accept_order'),
    path('accepted-orders/', AcceptedOrdersListView.as_view(), name='accepted-orders'), #accepted order - admin
    path('delivery-boy/<int:delivery_boy_id>/accepted-orders/', AcceptedOrdersByVendorListView.as_view(), name='delivery-boy-accepted-orders'),
    path('delivery-boy/<int:delivery_boy_id>/order/<str:order_id>/update-status/',
    UpdateOrderStatusView.as_view(),name='update-order-status'),
    path('delivery-boy/<int:delivery_boy_id>/orders/', DeliveryBoyOrderListView.as_view(), name='delivery-boy-order-list'),
    path('delivery-boy/<int:delivery_boy_id>/notifications/', DeliveryBoyNotificationListView.as_view(), name='delivery-boy-notifications'),
    path('delivery_boys/<int:delivery_boy_id>/accepted_orders/', AcceptedOrderListView.as_view(), name='accepted-orders-list'),
    path('delivery_boys/<int:delivery_boy_id>/orders/<int:order_id>/reject/', RejectOrderView.as_view(), name='reject-order'),
    path('delivery_boys/<int:delivery_boy_id>/rejected_orders/', RejecteddOrderListView.as_view(), name='rejected-orders-list'),


    path('admin/delivery-charges/', DeliveryChargesAPIView.as_view(), name='delivery-charges-list-create'),
    path('admin/delivery-charges/<int:pk>/', DeliveryChargesAPIView.as_view(), name='delivery-charges-detail'),
    path('admin/delivery-charges/calculate/', CalculateDeliveryChargeAPIView.as_view(), name='calculate-delivery-charge'),

]