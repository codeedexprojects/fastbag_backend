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


class DeliveryBoyListCreateView(generics.ListCreateAPIView):
    queryset = DeliveryBoy.objects.all()
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

class AcceptedOrdersListView(generics.ListAPIView):
    serializer_class = AcceptedOrderSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return OrderAssign.objects.filter(is_accepted=True).select_related('order', 'accepted_by')

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
            # Get all delivery charges
            delivery_charges = DeliveryCharges.objects.all()
            
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