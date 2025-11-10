from django.urls import path
from cart.views import *

urlpatterns = [
    path('view/', CartDetailView.as_view(), name='cart-detail'), #view
    path('add/', AddToCartView.as_view(), name='add-to-cart'), #add to cart
    path('remove/<int:pk>/', RemoveFromCartView.as_view(), name='remove-from-cart'), #cart details
    #filter cart by product type
    path('grocery-cart/', GroceryCartView.as_view(), name='cart-grocery'),
    path('dishes-cart/', DishCartView.as_view(), name='cart-dishes'),
    path('fashion-cart/', ClothingCartView.as_view(), name='cart-clothing'),
    #checkout
    path('checkout/', CheckoutView.as_view(), name='checkout'), #checkout
    path('orders/', CheckoutListView.as_view(), name='order-list'), #view orders
    path('orders/<int:pk>/', CheckoutDetailView.as_view(), name='order-detail'), #Order details
    path('orders/<int:pk>/cancel/', CancelOrderView.as_view(), name='cancel-order'), #order delete
    #orders
    path('orders/admin/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('user/orders/', UserOrderListView.as_view(), name='user-orders'),  # Get orders of logged-in user
    path('orders/update-status/<str:order_id>/', UpdateOrderStatusView.as_view(), name='update-order-status'),  # Admin can update order status
    path('order-list-admin/', AllorderviewAdmin.as_view(), name='0rder-list-admin'), #list all orders
    #orders by vendors
    path('vendor/orders/', VendorOrderListView.as_view(), name='vendor-orders'),
    path('vendor/orders/<str:order_id>/', VendorOrderDetailView.as_view(), name='vendor-order-detail'),#vendor order detail
    path('vendor/order-update/<str:order_id>/', VendorOrderUpdateDetailView.as_view(), name='vendor-order-detail'),

    # cart group
    path('cart/grouped/', GroupedCartView.as_view(), name='grouped-cart'),
    #single vendor cart
    path('cart/vendor/<int:vendor_id>/', VendorCartItemsView.as_view(), name='vendor-cart-items'),
    path('checkout/<int:vendor_id>/', VendorCheckoutView.as_view(), name='vendor-checkout'),#checkout
    path('order-verify-payment/', RazorpayPaymentVerifyView.as_view(), name='verify-payment'),#verify razorpay

    path('orders/<str:order_id>/', UserOrderDetailView.as_view(), name='user-order-detail'),#user order details
    # path('vendor/orders/', VendorOrderListView.as_view(), name='vendor-orders'),  #get vendor orders
    path('delete-all-orders/', DeleteAllOrdersView.as_view(), name='delete-all-orders'),#delete all orders
    path('orders/<str:order_id>/cancel/',CancelOrderItemView.as_view(),name='cancel-order'),#cancel whole order

    # URL for cancelling a specific item within an order
    path('orders/<str:order_id>/items/<int:item_id>/cancel/',CancelOrderItemView.as_view(),name='cancel-order-item'),
    path('orders/<str:order_id>/items/',OrderItemsByOrderIDView.as_view(),name='order-items-by-id'),
    #notifications
    path('notifications/', UserNotificationListView.as_view(), name='user-notifications'),
    path('notifications/read/<int:notification_id>/', MarkNotificationAsReadView.as_view(), name='mark-notification-read'),
    #for return
    path('orders/<str:order_id>/return/', ReturnOrderItemView.as_view(), name='return-order'),
    path('orders/<str:order_id>/delivery-boy/', get_delivery_boy_for_order, name='get-delivery-boy'),
    path('orders/<str:order_id>/assign-delivery-boy/', assign_delivery_boy, name='assign-delivery-boy'),
    path('delivery-boys/available/', get_available_delivery_boys, name='available-delivery-boys'),
    path('orders/<str:order_id>/items/<int:item_id>/return/', ReturnOrderItemView.as_view(), name='return-order-item'),
    path('orders/<str:order_id>/items/<int:item_id>/update-status/',UpdateOrderItemStatusView.as_view(),name='update-order-item-status'),
    path('vendor/notifications/', VendorNotificationListView.as_view(), name='vendor-notifications'),
    path('admin/users/<int:user_id>/orders/', AdminUserOrderListView.as_view(), name='admin-user-orders'),
    path('stats/monthly-orders/', MonthlyOrderStatsAPIView.as_view(), name='monthly-orders-stats'),
    path('stats/daily-revenue/', DailyRevenueComparisonAPIView.as_view(), name='daily-revenue-stats'),
    path('stats/overview/', OrderRevenueStatsAPIView.as_view(), name='order-revenue-stats'),
    path('stats/revenue-by-date/', RevenueBySpecificDateAPIView.as_view(), name='revenue-by-date'),
    path('stats/product-vendor-count/', ProductCountAPIView.as_view(), name='product-count'),
    #coupon apply/remove
    path('cart/vendor/<int:vendor_id>/apply-coupon/', ApplyCouponView.as_view(), name='apply-coupon'),
    path('cart/vendor/<int:vendor_id>/remove-coupon/', RemoveCouponView.as_view(), name='remove-coupon'),

    path('order-assign/<int:delivery_boy_id>/', OrderAssignByStatusAPIView.as_view(), name='order-assign-by-status'),

]


