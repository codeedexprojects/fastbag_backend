from django.shortcuts import render
from rest_framework import generics
from .models import DeliveryBoy
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
import random
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from vendors.authentication import VendorJWTAuthentication
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from decimal import Decimal
from vendors.models import VendorCommission


class DeliveryBoyListCreateView(generics.ListCreateAPIView):
    queryset = DeliveryBoy.objects.all().order_by('-id')
    serializer_class = DeliveryBoySerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save()

class DeliveryBoyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DeliveryBoy.objects.all()
    serializer_class = DeliveryBoySerializer
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


from rest_framework.views import APIView
# ---- Request OTP View ----
from users.utils import send_otp_2factor
class RequestOTPView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            mobile_number = serializer.validated_data['mobile_number']

            try:
                delivery_boy = DeliveryBoy.objects.get(mobile_number=mobile_number)
            except DeliveryBoy.DoesNotExist:
                return Response({"message": "No account found with this mobile number."},
                                status=status.HTTP_404_NOT_FOUND)

            # Hardcoded OTP for testing
            if mobile_number == "9876543210":
                otp = "123456"
            else:
                otp = str(random.randint(100000, 999999))

            delivery_boy.otp = otp
            delivery_boy.otp_created_at = timezone.now()
            delivery_boy.save()

            try:
                send_otp_2factor(mobile_number, otp)
            except Exception as e:
                return Response({"message": f"Failed to send OTP: {str(e)}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({"message": f"OTP sent successfully! OTP: {otp}"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginWithOTPView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        serializer = OTPLoginSerializer(data=request.data)
        if serializer.is_valid():
            mobile_number = serializer.validated_data['mobile_number']
            otp = serializer.validated_data['otp']
            fcm_token = serializer.validated_data.get('fcm_token', None)

            try:
                delivery_boy = DeliveryBoy.objects.get(mobile_number=mobile_number)
            except DeliveryBoy.DoesNotExist:
                return Response({"message": "No account found with this mobile number."},
                                status=status.HTTP_404_NOT_FOUND)

            if mobile_number == "9876543210" and otp == "123456":
                delivery_boy.otp = None
                delivery_boy.otp_created_at = None
                if fcm_token:
                    delivery_boy.fcm_token = fcm_token
                delivery_boy.save()
                return Response({
                    "message": "Login successful!",
                    "delivery_boy_id": delivery_boy.id,
                    "mobile_number": delivery_boy.mobile_number,
                    "name": delivery_boy.name,
                    "fcm_token": delivery_boy.fcm_token
                }, status=status.HTTP_200_OK)

            if delivery_boy.otp != otp:
                return Response({"message": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

            delivery_boy.otp = None
            delivery_boy.otp_created_at = None
            if fcm_token:
                delivery_boy.fcm_token = fcm_token
            delivery_boy.save()

            return Response({
                "message": "Login successful!",
                "delivery_boy_id": delivery_boy.id,
                "mobile_number": delivery_boy.mobile_number,
                "name": delivery_boy.name,
                "fcm_token": delivery_boy.fcm_token
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeliveryBoyLogoutView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        delivery_boy_id = request.data.get("delivery_boy_id")

        if not delivery_boy_id:
            return Response({"message": "Delivery boy ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            delivery_boy = DeliveryBoy.objects.get(id=delivery_boy_id)
        except DeliveryBoy.DoesNotExist:
            return Response({"message": "Invalid delivery boy ID."}, status=status.HTTP_404_NOT_FOUND)

        delivery_boy.is_active = False
        delivery_boy.otp = None
        delivery_boy.save()

        return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)

class UpdateDeliveryBoyStatusView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        delivery_boy_id = request.data.get("delivery_boy_id")
        is_active = request.data.get("is_active")

        # Validation checks
        if delivery_boy_id is None:
            return Response({"message": "Delivery boy ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        if is_active is None:
            return Response({"message": "is_active field is required (true/false)."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            delivery_boy = DeliveryBoy.objects.get(id=delivery_boy_id)
        except DeliveryBoy.DoesNotExist:
            return Response({"message": "Delivery boy not found."}, status=status.HTTP_404_NOT_FOUND)

        if isinstance(is_active, str):
            is_active = is_active.lower() in ['true', '1', 'yes']

        delivery_boy.is_active = is_active
        delivery_boy.save(update_fields=["is_active"])

        status_text = "activated" if is_active else "deactivated"
        return Response({"message": f"Delivery boy successfully {status_text}."}, status=status.HTTP_200_OK)

class DeliveryBoyDetailViewUser(generics.RetrieveUpdateDestroyAPIView):
    queryset = DeliveryBoy.objects.all()
    serializer_class = DeliveryBoySerializer
    permission_classes = []

    def get_object(self):
        delivery_boy_id = self.kwargs.get('delivery_boy_id')
        return DeliveryBoy.objects.get(id=delivery_boy_id)

# View for creating an order assignment
class OrderAssignCreateView(generics.CreateAPIView):
    queryset = OrderAssign.objects.all()
    serializer_class = OrderAssignSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

#assigned order list
class DeliveryBoyAssignedOrdersView(generics.ListAPIView):
    serializer_class = OrderAssignSerializer
    permission_classes= []


    def get_queryset(self):
        delivery_boy_id = self.kwargs['delivery_boy_id']
        return OrderAssign.objects.filter(delivery_boy_id=delivery_boy_id)

#order assign status-update
class OrderAssignStatusUpdateView(generics.UpdateAPIView):
    queryset = OrderAssign.objects.all()
    serializer_class = OrderAssignSerializer
    permission_classes = [IsAdminUser]

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


class OrderAssignStatusFilterView(generics.ListAPIView):
    serializer_class = OrderAssignSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        status = self.request.query_params.get('status')
        queryset = OrderAssign.objects.all()
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
class DeliveryBoyNotificationListView(APIView):
    permission_classes = []  

    def get(self, request, delivery_boy_id):
        try:
            delivery_boy = DeliveryBoy.objects.get(id=delivery_boy_id)
        except DeliveryBoy.DoesNotExist:
            return Response({'error': 'Delivery boy not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get orders assigned to THIS delivery boy with status 'ASSIGNED'
        assigned_order_ids = OrderAssign.objects.filter(
            delivery_boy=delivery_boy,
            status='ASSIGNED'
        ).values_list('order_id', flat=True)

        # Get notifications for this delivery boy's assigned orders
        notifications = DeliveryNotification.objects.filter(
            delivery_boy=delivery_boy,
            order_id__in=assigned_order_ids,
            is_read=False  # Only show unread notifications
        ).order_by('-created_at')
        
        serializer = DeliveryNotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MarkNotificationAsReadView(generics.UpdateAPIView):
    queryset = DeliveryNotification.objects.all()
    serializer_class = DeliveryNotificationSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        try:
            notification = self.get_object()
            notification.is_read = True
            notification.save()
            return Response({'message': 'Marked as read'}, status=status.HTTP_200_OK)
        except DeliveryNotification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

from django.shortcuts import get_object_or_404
from cart.models import Order

class AcceptOrderView(generics.UpdateAPIView):
    authentication_classes = []
    permission_classes = []

    def update(self, request, *args, **kwargs):
        order_id = kwargs.get('order_id')
        delivery_boy_id = kwargs.get('delivery_boy_id')

        # Get order and delivery boy
        order = get_object_or_404(Order, id=order_id)
        delivery_boy = get_object_or_404(DeliveryBoy, id=delivery_boy_id)

        # Check if order already accepted by another delivery boy
        if OrderAssign.objects.filter(order=order, is_accepted=True).exclude(delivery_boy=delivery_boy).exists():
            return Response(
                {"detail": "This order has already been accepted by another delivery boy."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the OrderAssign for this delivery boy and order
        try:
            order_assign = OrderAssign.objects.get(order=order, delivery_boy=delivery_boy)
        except OrderAssign.DoesNotExist:
            return Response(
                {"detail": "Order is not assigned to this delivery boy."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update order assignment
        order_assign.status = 'ACCEPTED'
        order_assign.is_accepted = True
        order_assign.accepted_by = delivery_boy
        order_assign.save()

        # Update order status
        order.order_status = 'ACCEPTED'
        order.save()

        # Mark notification as read
        DeliveryNotification.objects.filter(
            delivery_boy=delivery_boy,
            order=order
        ).update(is_read=True)

        # Reject/remove assignments for other delivery boys
        OrderAssign.objects.filter(order=order).exclude(delivery_boy=delivery_boy).update(
            status='REJECTED',
            is_rejected=True
        )

        return Response({
            "message": "Order accepted successfully.",
            "order_id": order.id,
            "order_number": order.order_id,
            "delivery_boy_id": delivery_boy.id,
            "delivery_boy_name": delivery_boy.name,
            "status": order_assign.status
        }, status=status.HTTP_200_OK)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AcceptedOrdersListView(generics.ListAPIView):
    """
    API view to retrieve all orders (accepted and rejected) for a specific delivery boy
    """
    serializer_class = AcceptedOrderSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        delivery_boy_id = self.kwargs.get('pk')
        
        # Return all assigned orders for this delivery boy
        queryset = OrderAssign.objects.filter(
            delivery_boy_id=delivery_boy_id
        ).select_related(
            'order',
            'order__user',
            'order__checkout',
            'delivery_boy',
            'accepted_by'
        ).prefetch_related(
            'order__order_items',
            'order__order_items__vendor'
        ).order_by('-assigned_at')
        
        # Optional filtering by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            if status_filter.lower() == 'accepted':
                queryset = queryset.filter(is_accepted=True, is_rejected=False)
            elif status_filter.lower() == 'rejected':
                queryset = queryset.filter(is_rejected=True)
            elif status_filter.lower() == 'pending':
                queryset = queryset.filter(is_accepted=False, is_rejected=False)
        
        return queryset

class AcceptedOrdersByVendorListView(generics.ListAPIView):
    serializer_class = AcceptedOrderSerializer
    authentication_classes = [VendorJWTAuthentication]
    def get_queryset(self):
        delivery_boy_id = self.kwargs.get('delivery_boy_id')

        orders = OrderAssign.objects.filter(
            is_accepted=True,
            accepted_by__id=delivery_boy_id
        ).select_related('order', 'order__checkout', 'accepted_by')

        return orders


class UpdateOrderStatusView(generics.UpdateAPIView):
    queryset = OrderAssign.objects.all()
    serializer_class = OrderAssignStatusUpdateSerializer
    permission_classes = []  

    def update(self, request, *args, **kwargs):
        delivery_boy_id = kwargs.get('delivery_boy_id')
        order_id = kwargs.get('order_id')  
        new_status = request.data.get('status')

        try:
            order_assign = OrderAssign.objects.get(
                order__order_id=order_id,     
                accepted_by__id=delivery_boy_id,
                is_accepted=True               
            )
        except OrderAssign.DoesNotExist:
            return Response(
                {"detail": "Assigned order not found or not accepted by this delivery boy."},
                status=status.HTTP_404_NOT_FOUND
            )

        valid_statuses = dict(OrderAssign._meta.get_field('status').choices)
        if new_status not in valid_statuses:
            return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)

        order_assign.status = new_status
        order_assign.save()

        return Response({
            "message": f"Order status updated to {new_status}.",
            "delivery_boy_id": delivery_boy_id,
            "order_id": order_id
        }, status=status.HTTP_200_OK)


class DeliveryBoyOrderListView(generics.ListAPIView):
    serializer_class = DeliveryNotificationSerializer
    permission_classes = []

    def get_queryset(self):
        delivery_boy_id = self.kwargs['delivery_boy_id']
        return DeliveryNotification.objects.filter(delivery_boy_id=delivery_boy_id).select_related('order')

class AcceptedOrderListView(generics.ListAPIView):
    serializer_class = AcceptedOrderSerializer
    permission_classes = []

    def get_queryset(self):
        delivery_boy_id = self.kwargs.get('delivery_boy_id')
        return OrderAssign.objects.filter(
            is_accepted=True,
            accepted_by_id=delivery_boy_id
        ).select_related('order', 'accepted_by', 'order__checkout', 'order__user')

class RejectOrderView(generics.UpdateAPIView):
    permission_classes = []

    def update(self, request, *args, **kwargs):
        order_id = kwargs.get('order_id')
        delivery_boy_id = kwargs.get('delivery_boy_id')

        order = get_object_or_404(Order, id=order_id)
        delivery_boy = get_object_or_404(DeliveryBoy, id=delivery_boy_id)

        order_assignment = (
            OrderAssign.objects.filter(order=order, delivery_boy=delivery_boy)
            .order_by('-assigned_at')
            .first()
        )

        if not order_assignment:
            order_assignment = OrderAssign.objects.create(
                order=order,
                delivery_boy=delivery_boy,
                assigned_at=timezone.now(),
                status='REJECTED',
                is_rejected=True
            )
        else:
            if order_assignment.is_accepted:
                return Response(
                    {"detail": "This order is already accepted and cannot be rejected."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if order_assignment.is_rejected:
                return Response(
                    {"detail": "This order is already marked as rejected by this delivery boy."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            order_assignment.is_rejected = True
            order_assignment.status = 'REJECTED'
            order_assignment.save()

        return Response({
            "message": "Order rejected successfully.",
            "order_id": order.id,
            "delivery_boy_id": delivery_boy.id,
            "delivery_boy_name": delivery_boy.name,
            "status": order_assignment.status
        }, status=status.HTTP_200_OK)

class RejecteddOrderListView(generics.ListAPIView):
    serializer_class = AcceptedOrderSerializer
    permission_classes = []

    def get_queryset(self):
        delivery_boy_id = self.kwargs.get('delivery_boy_id')
        return OrderAssign.objects.filter(
            is_rejected=True,
            delivery_boy_id=delivery_boy_id
        ).select_related('order', 'delivery_boy', 'order__checkout', 'order__user')
    



class DeliveryChargesAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            # Get specific delivery charge by ID
            delivery_charge = get_object_or_404(DeliveryCharges, pk=pk)
            serializer = DeliveryChargesSerializer(delivery_charge)
            return Response({
                'success': True,
                'message': 'Delivery charge retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        else:
            # Get all delivery charges, ordered by distance_from
            delivery_charges = DeliveryCharges.objects.all().order_by('distance_from')
            
            # Optional filtering by active status
            is_active = request.query_params.get('is_active', None)
            if is_active is not None:
                is_active_bool = is_active.lower() == 'true'
                delivery_charges = delivery_charges.filter(is_active=is_active_bool)
            
            serializer = DeliveryChargesSerializer(delivery_charges, many=True)
            return Response({
                'success': True,
                'message': 'Delivery charges retrieved successfully',
                'count': delivery_charges.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = DeliveryChargesSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Delivery charge created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Validation error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        delivery_charge = get_object_or_404(DeliveryCharges, pk=pk)
        serializer = DeliveryChargesSerializer(delivery_charge, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Delivery charge updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Validation error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        delivery_charge = get_object_or_404(DeliveryCharges, pk=pk)
        serializer = DeliveryChargesSerializer(
            delivery_charge, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Delivery charge updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Validation error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        delivery_charge = get_object_or_404(DeliveryCharges, pk=pk)
        delivery_charge.delete()
        
        return Response({
            'success': True,
            'message': 'Delivery charge deleted successfully'
        }, status=status.HTTP_200_OK)


class CalculateDeliveryChargeAPIView(APIView):
    
    def post(self, request):
        distance = request.data.get('distance')
        is_night = request.data.get('is_night', False)
        
        if distance is None:
            return Response({
                'success': False,
                'message': 'Distance is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            distance = float(distance)
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'message': 'Invalid distance value'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find matching delivery charge
        delivery_charge = DeliveryCharges.objects.filter(
            distance_from__lte=distance,
            distance_to__gte=distance,
            is_active=True
        ).first()
        
        if not delivery_charge:
            return Response({
                'success': False,
                'message': f'No delivery charge found for distance {distance}km'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate charge based on time
        charge = delivery_charge.night_charge if is_night else delivery_charge.day_charge
        
        return Response({
            'success': True,
            'message': 'Delivery charge calculated successfully',
            'data': {
                'distance': distance,
                'is_night': is_night,
                'charge': float(charge),
                'charge_type': 'night' if is_night else 'day',
                'distance_range': f"{delivery_charge.distance_from}km - {delivery_charge.distance_to}km"
            }
        }, status=status.HTTP_200_OK)
    



from django.db import transaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class DeliverOrderView(generics.UpdateAPIView):
    permission_classes = []
    
    def update(self, request, *args, **kwargs):
        delivery_boy_id = kwargs.get('delivery_boy_id')
        order_id = kwargs.get('order_id')

        try:
            order_assign = OrderAssign.objects.get(
                order__order_id=order_id,
                accepted_by__id=delivery_boy_id,
                is_accepted=True
            )
        except OrderAssign.DoesNotExist:
            return Response(
                {"detail": "Assigned order not found or not accepted by this delivery boy."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if order is already delivered
        if order_assign.status == 'DELIVERED':
            return Response(
                {"detail": "Order is already delivered."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update order assignment status to DELIVERED
        order_assign.status = 'DELIVERED'
        order_assign.save()

        # Update main order status
        order = order_assign.order
        order.order_status = 'delivered'
        order.save()

        # Update all order items status to delivered
        order.order_items.exclude(status='cancelled').update(status='delivered')

        # Calculate and create vendor commissions
        commission_details = self.create_vendor_commissions(order)

        return Response({
            "message": "Order delivered successfully.",
            "order_id": order_id,
            "delivery_boy_id": delivery_boy_id,
            "commissions_created": commission_details
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def create_vendor_commissions(self, order):
        """
        Calculate and create commission record for the vendor
        """
        try:
            # Get first active order item
            first_item = order.order_items.exclude(status='cancelled').first()
            
            if not first_item:
                logger.error(f"No active items found for order {order.order_id}")
                return None
            
            logger.info(f"First item: product_id={first_item.product_id}, product_type={first_item.product_type}")
            
            # Get vendor based on product type
            vendor = None
            
            if first_item.product_type == 'Fashion':
                try:
                    clothing = Clothing.objects.select_related('vendor').get(id=first_item.product_id)
                    vendor = clothing.vendor
                    logger.info(f"Found clothing vendor: {vendor.business_name}")
                except Clothing.DoesNotExist:
                    logger.error(f"Clothing with id {first_item.product_id} not found")
                    
            elif first_item.product_type == 'Restaurant':
                try:
                    dish = Dish.objects.select_related('vendor').get(id=first_item.product_id)
                    vendor = dish.vendor
                    logger.info(f"Found dish vendor: {vendor.business_name}")
                except Dish.DoesNotExist:
                    logger.error(f"Dish with id {first_item.product_id} not found")
                    
            elif first_item.product_type == 'Grocery':
                try:
                    grocery = GroceryProducts.objects.select_related('vendor').get(id=first_item.product_id)
                    vendor = grocery.vendor
                    logger.info(f"Found grocery vendor: {vendor.business_name}")
                except GroceryProducts.DoesNotExist:
                    logger.error(f"Grocery with id {first_item.product_id} not found")
            
            if not vendor:
                logger.error(f"No vendor found for product_id {first_item.product_id}, product_type {first_item.product_type}")
                return None
            
            # Get vendor's commission percentage
            vendor_commission = vendor.commission if vendor.commission else Decimal('0.00')
            
            logger.info(f"Vendor commission: {vendor_commission}%")
            
            # Use order's final amount for commission calculation
            final_amount = Decimal(str(order.final_amount))
            
            # Calculate commission amount
            commission_amount = (final_amount * vendor_commission) / Decimal('100')
            
            logger.info(f"Final amount: {final_amount}, Commission amount: {commission_amount}")
            
            # Create commission record
            vendor_comm = VendorCommission.objects.create(
                vendor=vendor,
                commission_percentage=vendor_commission,
                commission_amount=commission_amount,
                total_sales=final_amount,
                payment_status='pending'
            )
            
            logger.info(f"Commission created successfully: ID {vendor_comm.id}")
            
            # Return commission details
            return {
                'commission_id': vendor_comm.id,
                'vendor_id': vendor.id,
                'vendor_name': vendor.business_name,
                'total_sales': str(final_amount),
                'commission_percentage': str(vendor_commission),
                'commission_amount': str(commission_amount)
            }
            
        except Exception as e:
            logger.error(f"Error creating commission: {str(e)}", exc_info=True)
            return None
        





from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from math import radians, sin, cos, sqrt, atan2
from decimal import Decimal
from .models import DeliveryBoy, OrderAssign
from cart.models import Order
from users.models import Address 
from .serializers import DeliveryBoySerializer, OrderAssignSerializer


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points on Earth using the Haversine formula.
    Returns distance in kilometers.
    """
    # Convert to float for calculation
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    
    # Radius of Earth in kilometers
    R = 6371.0
    
    # Convert coordinates to radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = R * c
    return distance


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_delivery_boys_for_order(request, order_id):
    """
    Get list of available delivery boys whose service radius covers the order's delivery location.
    """
    try:
        # Change this line - use database ID instead of order_id field
        order = get_object_or_404(Order, id=order_id) 
        
        # Get the order's delivery address
        if not order.address:
            return Response({
                'success': False,
                'message': 'Order does not have an associated address'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        order_address = order.address
        
        # Check if address has coordinates
        if not order_address.latitude or not order_address.longitude:
            return Response({
                'success': False,
                'message': 'Order address does not have valid coordinates'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all active delivery boys with valid coordinates and radius
        all_delivery_boys = DeliveryBoy.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
            radius_km__isnull=False
        )
        
        # Filter delivery boys whose service area covers the order location
        available_boys = []
        order_lat = float(order_address.latitude)
        order_lon = float(order_address.longitude)
        
        for boy in all_delivery_boys:
            # Calculate distance from delivery boy's base location to order delivery location
            distance = calculate_distance(
                float(boy.latitude),
                float(boy.longitude),
                order_lat,
                order_lon
            )
            
            # Check if order delivery location is within delivery boy's service radius
            service_radius = float(boy.radius_km)
            
            if distance <= service_radius:
                # Check if delivery boy is currently available
                is_currently_available = not OrderAssign.objects.filter(
                    delivery_boy=boy,
                    status__in=['ASSIGNED', 'ACCEPTED', 'PICKED', 'ON_THE_WAY']
                ).exists()
                
                boy_data = {
                    'id': boy.id,
                    'name': boy.name,
                    'phone_number': boy.mobile_number,
                    'email': boy.email,
                    'profile_image': request.build_absolute_uri(boy.photo.url) if boy.photo else None,
                    'vehicle_type': boy.vehicle_type,
                    'vehicle_number': boy.vehicle_number,
                    'place': boy.place,
                    'base_latitude': float(boy.latitude),
                    'base_longitude': float(boy.longitude),
                    'service_radius_km': service_radius,
                    'distance_to_delivery_location_km': round(distance, 2),
                    'is_available': is_currently_available
                }
                available_boys.append(boy_data)
        
        # Sort by distance (closest delivery boys first)
        available_boys.sort(key=lambda x: x['distance_to_delivery_location_km'])
        
        return Response({
            'success': True,
            'delivery_boys': available_boys,
            'total_count': len(available_boys),
            'order_delivery_location': {
                'latitude': order_lat,
                'longitude': order_lon,
                'address': str(order_address)
            }
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_delivery_boy_to_order(request, order_id):
    """
    Assign a delivery boy to an order.
    Validates that the order location is within the delivery boy's service radius.
    Expected payload: {
        "delivery_boy_id": <int>,
        "message": <string> (optional)
    }
    """
    try:
        # Get the order
        order = get_object_or_404(Order, id=order_id)
        
        # Get delivery boy ID from request
        delivery_boy_id = request.data.get('delivery_boy_id')
        notification_message = request.data.get('message', f'New order #{order_id} assigned to you')
        
        if not delivery_boy_id:
            return Response({
                'success': False,
                'message': 'Delivery boy ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the delivery boy
        delivery_boy = get_object_or_404(DeliveryBoy, id=delivery_boy_id, is_active=True)
        
        # Validate that order location is within delivery boy's service radius
        if order.address and order.address.latitude and order.address.longitude:
            if delivery_boy.latitude and delivery_boy.longitude and delivery_boy.radius_km:
                distance = calculate_distance(
                    delivery_boy.latitude,
                    delivery_boy.longitude,
                    order.address.latitude,
                    order.address.longitude
                )
                
                if distance > float(delivery_boy.radius_km):
                    return Response({
                        'success': False,
                        'message': f'Order location is outside delivery boy\'s service radius. Distance: {round(distance, 2)}km, Service Radius: {float(delivery_boy.radius_km)}km'
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if order already has an active assignment
        existing_assignment = OrderAssign.objects.filter(
            order=order,
            status__in=['ASSIGNED', 'ACCEPTED', 'PICKED', 'ON_THE_WAY']
        ).first()
        
        if existing_assignment:
            return Response({
                'success': False,
                'message': f'Order already assigned to {existing_assignment.delivery_boy.name}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate delivery charge based on distance
        delivery_charge = Decimal('50.00')  # Base charge
        
        if order.address and order.address.latitude and order.address.longitude:
            if delivery_boy.latitude and delivery_boy.longitude:
                distance = calculate_distance(
                    delivery_boy.latitude,
                    delivery_boy.longitude,
                    order.address.latitude,
                    order.address.longitude
                )
                # Base ₹50 + ₹10 per km
                delivery_charge = Decimal('50.00') + (Decimal(str(distance)) * Decimal('10.00'))
        
        # Create order assignment
        order_assign = OrderAssign.objects.create(
            order=order,
            delivery_boy=delivery_boy,
            status='ASSIGNED',
            delivery_charge=delivery_charge
        )
        
        # Update order status if needed
        if order.order_status == 'pending':
            order.order_status = 'processing'
            order.save()
        
        # TODO: Send FCM notification to delivery boy
        # if delivery_boy.fcm_token:
        #     send_fcm_notification(
        #         token=delivery_boy.fcm_token,
        #         title="New Order Assigned",
        #         body=notification_message,
        #         data={'order_id': order_id, 'type': 'order_assigned'}
        #     )
        
        # Prepare response data
        delivery_boy_data = {
            'id': delivery_boy.id,
            'name': delivery_boy.name,
            'phone_number': delivery_boy.mobile_number,
            'email': delivery_boy.email,
            'profile_image': request.build_absolute_uri(delivery_boy.photo.url) if delivery_boy.photo else None,
            'vehicle_type': delivery_boy.vehicle_type,
            'vehicle_number': delivery_boy.vehicle_number,
            'place': delivery_boy.place,
            'base_latitude': float(delivery_boy.latitude) if delivery_boy.latitude else None,
            'base_longitude': float(delivery_boy.longitude) if delivery_boy.longitude else None,
            'service_radius_km': float(delivery_boy.radius_km) if delivery_boy.radius_km else None,
            'is_available': False  # Now assigned
        }
        
        return Response({
            'success': True,
            'message': f'Order successfully assigned to {delivery_boy.name}',
            'delivery_boy': delivery_boy_data,
            'assignment': {
                'id': order_assign.id,
                'assigned_at': order_assign.assigned_at,
                'status': order_assign.status,
                'delivery_charge': float(order_assign.delivery_charge)
            }
        }, status=status.HTTP_201_CREATED)
        
    except Order.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except DeliveryBoy.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Delivery boy not found or inactive'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_delivery_boy(request, order_id):
    """
    Get the assigned delivery boy for a specific order.
    """
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Get active assignment
        assignment = OrderAssign.objects.filter(
            order=order,
            status__in=['ASSIGNED', 'ACCEPTED', 'PICKED', 'ON_THE_WAY']
        ).first()
        
        if not assignment:
            return Response({
                'success': True,
                'delivery_boy': None,
                'message': 'No delivery boy assigned to this order'
            }, status=status.HTTP_200_OK)
        
        delivery_boy = assignment.delivery_boy
        
        delivery_boy_data = {
            'id': delivery_boy.id,
            'name': delivery_boy.name,
            'phone_number': delivery_boy.mobile_number,
            'email': delivery_boy.email,
            'profile_image': request.build_absolute_uri(delivery_boy.photo.url) if delivery_boy.photo else None,
            'vehicle_type': delivery_boy.vehicle_type,
            'vehicle_number': delivery_boy.vehicle_number,
            'place': delivery_boy.place,
            'base_latitude': float(delivery_boy.latitude) if delivery_boy.latitude else None,
            'base_longitude': float(delivery_boy.longitude) if delivery_boy.longitude else None,
            'service_radius_km': float(delivery_boy.radius_km) if delivery_boy.radius_km else None,
            'is_available': False,
            'assignment': {
                'id': assignment.id,
                'assigned_at': assignment.assigned_at,
                'status': assignment.status,
                'delivery_charge': float(assignment.delivery_charge)
            }
        }
        
        return Response({
            'success': True,
            'delivery_boy': delivery_boy_data
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)