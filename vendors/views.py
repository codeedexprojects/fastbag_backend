from django.shortcuts import render
from rest_framework import generics ,status ,viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import *
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import IsAdminUser
from django.core.mail import send_mail
import random
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import authenticate
from rest_framework_simplejwt.authentication import JWTAuthentication
from users.permissions import IsVendor
from rest_framework.permissions import BasePermission
from vendors.models import Vendor
from vendors.authentication import VendorJWTAuthentication
from groceryproducts.serializers import GroceryProductSerializer
from foodproduct.serializers import DishCreateSerializer
from fashion.serializers import ClothingSerializer
from groceryproducts.models import GroceryProducts
from fashion.models import Clothing
from foodproduct.models import Dish
from rest_framework.exceptions import PermissionDenied
from vendors.pagination import CustomPageNumberPagination
from rest_framework import generics, filters
from rest_framework.pagination import PageNumberPagination
from decimal import Decimal,InvalidOperation
from geopy.distance import distance as geopy_distance
from geopy.distance import geodesic
from math import radians, sin, cos, sqrt, atan2
from django.shortcuts import get_object_or_404
from django.db.models import Sum, F
from users.utils import send_otp_2factor
from django.http import QueryDict
from decimal import Decimal
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)
class IsVendor(BasePermission):


    def has_permission(self, request, view):
        user = request.user
        if user and user.is_authenticated:
            return isinstance(user, Vendor)
        return False


#for creating and displaying stores
class StoreTypeListCreateView(generics.ListCreateAPIView):
    pagination_class = None
    permission_classes = [IsAuthenticated,IsAdminUser]
    queryset = StoreType.objects.all().order_by('-created_at')
    serializer_class = StoreTypeSerializer


class StoreTypeListView(generics.ListAPIView):
    permission_classes = []
    queryset = StoreType.objects.all().order_by('-created_at')
    serializer_class = StoreTypeSerializer

class StoreDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = StoreType.objects.all()
    serializer_class = StoreTypeSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"message": "Store details retrieved successfully.", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {"message": "Store details updated successfully.", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Store deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


class VendorListCreateView(APIView):
    """API view for creating and listing vendors"""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        """Create a new vendor"""
        # Use request.POST for form data and request.FILES for files
        # This avoids the pickle error completely
        data = {}
        
        # Copy POST data (non-file fields)
        for key in request.POST.keys():
            data[key] = request.POST.get(key)
        
        # Add FILES data (file fields)
        for key in request.FILES.keys():
            data[key] = request.FILES.get(key)

        # Convert time from 12-hour format (e.g., '10:00 PM') to 24-hour format
        if 'opening_time' in data and data['opening_time']:
            try:
                # Handle both "10:00 PM" and "10:00" formats
                time_str = str(data['opening_time']).strip()
                if 'AM' in time_str.upper() or 'PM' in time_str.upper():
                    opening_time_obj = datetime.strptime(time_str, '%I:%M %p').time()
                    data['opening_time'] = opening_time_obj
                # else: already in 24-hour format, leave as is
            except ValueError as e:
                return Response(
                    {"opening_time": ["Invalid time format. Use format like '10:00 AM' or '02:30 PM'"]},
                    status=400
                )

        if 'closing_time' in data and data['closing_time']:
            try:
                # Handle both "10:00 PM" and "10:00" formats
                time_str = str(data['closing_time']).strip()
                if 'AM' in time_str.upper() or 'PM' in time_str.upper():
                    closing_time_obj = datetime.strptime(time_str, '%I:%M %p').time()
                    data['closing_time'] = closing_time_obj
                # else: already in 24-hour format, leave as is
            except ValueError as e:
                return Response(
                    {"closing_time": ["Invalid time format. Use format like '10:00 PM' or '11:30 PM'"]},
                    status=400
                )

        # Validate and clean latitude/longitude
        if 'latitude' in data and data['latitude']:
            try:
                lat_value = Decimal(str(data['latitude']))
                if lat_value < -90 or lat_value > 90:
                    return Response(
                        {"latitude": ["Latitude must be between -90 and 90"]},
                        status=400
                    )
                # Truncate to 10 decimal places
                data['latitude'] = lat_value.quantize(Decimal('0.0000000001'))
            except (InvalidOperation, ValueError):
                return Response(
                    {"latitude": ["Invalid latitude value"]},
                    status=400
                )

        if 'longitude' in data and data['longitude']:
            try:
                lng_value = Decimal(str(data['longitude']))
                if lng_value < -180 or lng_value > 180:
                    return Response(
                        {"longitude": ["Longitude must be between -180 and 180"]},
                        status=400
                    )
                # Truncate to 10 decimal places
                data['longitude'] = lng_value.quantize(Decimal('0.0000000001'))
            except (InvalidOperation, ValueError):
                return Response(
                    {"longitude": ["Invalid longitude value"]},
                    status=400
                )

        # Create serializer with the processed data
        serializer = VendorCreateSerializer(
            data=data,
            context={'request': request}
        )

        if serializer.is_valid():
            # Save the vendor
            vendor = serializer.save()

            # Return the serialized data with file URLs
            return Response(
                VendorCreateSerializer(vendor, context={'request': request}).data,
                status=201
            )

        return Response(serializer.errors, status=400)

    def get(self, request, *args, **kwargs):
        """List all vendors"""
        vendors = Vendor.objects.all().order_by('-created_at')
        serializer = VendorCreateSerializer(vendors, many=True, context={'request': request})
        return Response(serializer.data, status=200)



class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

class VendorListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Vendor.objects.all()
    serializer_class = VendorHomePageSerializer
    pagination_class = CustomPageNumberPagination

    def get_serializer_context(self):
        return {'request': self.request}


class VendorListViewAdmin(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    queryset = Vendor.objects.all()
    serializer_class = VendorCreateSerializer
    pagination_class = None

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance using Haversine formula"""
        R = 6371.0  # Earth's radius in km
        
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c

    def get_queryset(self):
        queryset = super().get_queryset()
        
        lat = self.request.query_params.get('latitude', None)
        lng = self.request.query_params.get('longitude', None)
        radius = self.request.query_params.get('radius', None)
        
        print(f"\n{'='*50}")
        print(f"GET_QUERYSET - Params received:")
        print(f"  latitude: {lat}")
        print(f"  longitude: {lng}")
        print(f"  radius: {radius}")
        
        if lat and lng and radius:
            try:
                user_lat = float(lat)
                user_lng = float(lng)
                radius_km = float(radius)
                
                print(f"Filtering vendors within {radius_km}km of ({user_lat}, {user_lng})")
                
                vendors_with_location = queryset.filter(
                    latitude__isnull=False,
                    longitude__isnull=False
                ).exclude(latitude=0, longitude=0)
                
                print(f"Vendors with coordinates: {vendors_with_location.count()}")
                
                filtered_ids = []
                for vendor in vendors_with_location:
                    try:
                        v_lat = float(vendor.latitude)
                        v_lng = float(vendor.longitude)
                        distance = self.calculate_distance(user_lat, user_lng, v_lat, v_lng)
                        
                        if distance <= radius_km:
                            filtered_ids.append(vendor.id)
                            print(f"  ✓ {vendor.business_name}: {distance:.2f}km")
                        else:
                            print(f"  ✗ {vendor.business_name}: {distance:.2f}km (too far)")
                    except (ValueError, TypeError) as e:
                        print(f"  ✗ {vendor.business_name}: Invalid coordinates")
                
                queryset = queryset.filter(id__in=filtered_ids)
                print(f"Returning {queryset.count()} filtered vendors")
                
            except (ValueError, TypeError) as e:
                print(f"ERROR parsing params: {e}")
        else:
            print("No location filter - returning all vendors")
        
        print(f"{'='*50}\n")
        return queryset

    def list(self, request, *args, **kwargs):
        """CRITICAL: This method MUST add distance_km to response"""
        
        # Get filtered queryset
        queryset = self.get_queryset()
        
        # Serialize vendors
        serializer = self.get_serializer(queryset, many=True)
        data = list(serializer.data)  # Convert to list to modify
        
        # Get location params
        lat = request.query_params.get('latitude', None)
        lng = request.query_params.get('longitude', None)
        
        print(f"\n{'='*50}")
        print(f"LIST METHOD - Adding distance_km field")
        print(f"  latitude param: {lat}")
        print(f"  longitude param: {lng}")
        print(f"  Total vendors to process: {len(data)}")
        
        if lat and lng:
            try:
                user_lat = float(lat)
                user_lng = float(lng)
                
                print(f"  Processing distances for location: ({user_lat}, {user_lng})")
                
                success_count = 0
                for vendor_data in data:
                    v_lat = vendor_data.get('latitude')
                    v_lng = vendor_data.get('longitude')
                    
                    if v_lat is not None and v_lng is not None:
                        try:
                            # Convert to float and calculate
                            v_lat_float = float(v_lat)
                            v_lng_float = float(v_lng)
                            
                            distance = self.calculate_distance(
                                user_lat, user_lng,
                                v_lat_float, v_lng_float
                            )
                            
                            vendor_data['distance_km'] = round(distance, 2)
                            success_count += 1
                            print(f"  ✓ {vendor_data['business_name']}: {distance:.2f}km")
                            
                        except (ValueError, TypeError) as e:
                            vendor_data['distance_km'] = None
                            print(f"  ✗ {vendor_data['business_name']}: Error - {e}")
                    else:
                        vendor_data['distance_km'] = None
                        print(f"  ✗ {vendor_data['business_name']}: No coordinates")
                
                print(f"  SUCCESS: Added distance_km to {success_count}/{len(data)} vendors")
                
                # Sort by distance
                data.sort(key=lambda x: x['distance_km'] if x['distance_km'] is not None else float('inf'))
                print(f"  Sorted by distance")
                
            except (ValueError, TypeError) as e:
                print(f"  ERROR: {e}")
                for vendor_data in data:
                    vendor_data['distance_km'] = None
        else:
            print(f"  No location params - setting all distance_km to None")
            for vendor_data in data:
                vendor_data['distance_km'] = None
        
        print(f"{'='*50}\n")
        
        # Return the modified data
        return Response(data)

class VendorDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = VendorDetailSerializer
    
    def get_queryset(self):
        return Vendor.objects.filter(id=self.request.user.id).order_by('-created_at')

class VendorPendingDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = VendorPendingDetailSerializer
    def get_queryset(self):
        return Vendor.objects.all()

    def get_object(self):
        vendor_id = self.kwargs.get("pk")
        try:
            return Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Vendor not found.")

class VendorDetailViewAdmin(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = VendorDetailSerializer
    pagination_class = None

    def get_queryset(self):
        return Vendor.objects.all()

    def get_object(self):
        vendor_id = self.kwargs.get("pk")
        try:
            return Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Vendor not found.")


#for accept - reject stores
class VendorAdminAcceptReject(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated,IsAdminUser]
    queryset = Vendor.objects.all()
    serializer_class = VendorDetailSerializer

    def update(self, request, *args, **kwargs):
        vendor = self.get_object()
        approval_status = request.data.get('is_approved', None)
        if approval_status is not None:
            if approval_status not in [True, False]:
                return Response({'error': 'Invalid status. Must be a boolean (True/False).'}, status=status.HTTP_400_BAD_REQUEST)
            vendor.is_approved = approval_status
            vendor.save()
            if approval_status:
                return Response({'status': 'Vendor registration approved.'}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'Vendor registration rejected.'}, status=status.HTTP_200_OK)
        return Response({'error': 'Missing approval status.'}, status=status.HTTP_400_BAD_REQUEST)

#for enable or disable vendors-Admin
class VendorEnableDisableView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = Vendor.objects.all()
    serializer_class = VendorDetailSerializer

    def update(self, request, *args, **kwargs):
        vendor = self.get_object()
        enable_status = request.data.get('is_active')
        if isinstance(enable_status, str):
            enable_status = enable_status.lower() in ["true", "1"]
        if enable_status not in [True, False]:
            return Response({'error': 'Invalid status. Must be a boolean (True/False).'}, status=status.HTTP_400_BAD_REQUEST)
        vendor.is_active = enable_status
        vendor.save()
        message = 'Vendor status enabled.' if enable_status else 'Vendor status disabled.'
        return Response({'status': message}, status=status.HTTP_200_OK)

#favourite vendor
class VendorFavouriteView(generics.UpdateAPIView):
    queryset = Vendor.objects.all()
    serializer_class = VendorDetailSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        vendor = self.get_object()
        favourite = request.data.get('is_favourite')

        if isinstance(favourite, str):
            favourite = favourite.lower() in ["true", "1"]

        if favourite not in [True, False]:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        if favourite:
            user.favourite_vendors.add(vendor)
            message = 'Vendor added to favourite'
        else:
            user.favourite_vendors.remove(vendor)
            message = 'Vendor removed from favourite'

        return Response({'status': message, 'vendor_id': vendor.id}, status=status.HTTP_200_OK)

class UserFavouriteVendorsView(generics.ListAPIView):
    serializer_class = VendorfavSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return self.request.user.favourite_vendors.all()


#for filtering rejected and accepted vendors
class VendorFilterListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Vendor.objects.all()
    serializer_class = VendorDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.query_params.get('status', None)

        if status:
            queryset = queryset.filter(is_approved=status)

        return queryset

#for viewing vendor by store category
class StoresByTypeView(generics.ListAPIView):
    serializer_class = VendorNameSerializer
    permission_classes=[]

    def get_queryset(self):
        store_type_id = self.kwargs.get('store_type_id')
        return Vendor.objects.filter(store_type_id=store_type_id, is_approved='True')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

# class VendorByCategoryListView(generics.ListAPIView):
#     serializer_class = VendorSerializer

#     def get_queryset(self):
#         category_name = self.kwargs.get('category_name')
#         return Vendor.objects.filter(category__name=category_name)

class VendorLoginView(APIView):
    """
    Send OTP to vendor's mobile number using custom OTP
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VendorLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile_number = serializer.validated_data['mobile_number']

        try:
            vendor_admin = Vendor.objects.get(contact_number=mobile_number)
        except Vendor.DoesNotExist:
            return Response(
                {"error": "Vendor not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if not vendor_admin.is_approved:
            return Response(
                {"error": "Your account has not been approved yet. Please contact support."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Generate 4-digit OTP (matching your field size)
            otp = str(random.randint(1000, 9999))
            
            # Send OTP via 2Factor
            send_otp_2factor(vendor_admin.contact_number, otp)
            
            # Store OTP in database
            vendor_admin.otp = otp
            vendor_admin.otp_created_at = timezone.now()
            vendor_admin.save()
            
            logger.info(f"OTP {otp} sent to {mobile_number}")
            
        except Exception as e:
            logger.error(f"Error sending OTP to {mobile_number}: {str(e)}")
            return Response(
                {"error": f"Failed to send OTP: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": "OTP sent successfully to your mobile number",
            # Remove this line in production for security!
            "otp": otp  # Only for testing
        }, status=status.HTTP_200_OK)


class VendorOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VendorOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile_number = serializer.validated_data['mobile_number']
        otp_input = str(serializer.validated_data['otp']).strip()
        fcm_token = serializer.validated_data.get('fcm_token')

        try:
            vendor_admin = Vendor.objects.get(contact_number=mobile_number)
        except Vendor.DoesNotExist:
            return Response(
                {"error": "Vendor not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # OTP existence
        if not vendor_admin.otp:
            return Response(
                {"error": "No OTP found. Please request a new OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # OTP expiration (10 minutes)
        if vendor_admin.otp_created_at:
            otp_age = timezone.now() - vendor_admin.otp_created_at
            if otp_age.total_seconds() > 600:
                vendor_admin.otp = None
                vendor_admin.otp_created_at = None
                vendor_admin.save()
                return Response(
                    {"error": "OTP has expired. Please request a new OTP."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        stored_otp = str(vendor_admin.otp).strip()
        if stored_otp != otp_input:
            return Response(
                {"error": "Invalid OTP. Please check and try again."},
                status=status.HTTP_400_BAD_REQUEST
            )

        vendor_admin.otp = None
        vendor_admin.otp_created_at = None

        # Update FCM token
        if fcm_token:
            vendor_admin.fcm_token = fcm_token

        vendor_admin.save()

        # Generate JWT token
        refresh = RefreshToken.for_user(vendor_admin)
        refresh["user_id"] = vendor_admin.id

        store = StoreType.objects.filter(vendor=vendor_admin).first()
        store_name = store.name if store else None

        return Response({
            "message": "Login successful",
            "vendor_id": vendor_admin.id,
            "store": store_name,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "is_approved": vendor_admin.is_approved,
            "fcm_token":vendor_admin.fcm_token
        }, status=status.HTTP_200_OK)

    


from rest_framework_simplejwt.views import TokenRefreshView
class VendorTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class VendorApprovalStatusView(APIView):
    permission_classes = []
    def get(self, request, id):
        try:
            vendor = Vendor.objects.get(id=id)
        except Vendor.DoesNotExist:
            return Response({"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = VendorApprovalStatusSerializer(vendor)
        return Response(serializer.data, status=status.HTTP_200_OK)


def send_otp_to_email(email, otp):
    subject = "Your OTP for Login"
    message = f"Your OTP is {otp}. It is valid for 10 minutes."
    from_email = "noreply@yourdomain.com"
    send_mail(subject, message, from_email, [email])


from django.utils.timezone import now, timedelta
class ForgotEmailSendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        alternate_email = request.data.get('alternate_email')

        if not alternate_email:
            return Response({"error": "Alternate email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vendor = Vendor.objects.get(alternate_email=alternate_email)
        except Vendor.DoesNotExist:
            return Response({"error": "Vendor with this alternate email not found."}, status=status.HTTP_404_NOT_FOUND)

        # Generate OTP
        otp = str(random.randint(1000, 9999))
        vendor.otp = otp
        vendor.otp_expiry = now() + timedelta(minutes=10)
        vendor.save()

        # Send OTP (replace with actual email service)
        send_otp_to_email(alternate_email, otp)

        return Response({"message": "OTP sent to alternate email."}, status=status.HTTP_200_OK)

class ForgotEmailVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        alternate_email = request.data.get('alternate_email')
        otp = request.data.get('otp')

        if not alternate_email or not otp:
            return Response({"error": "Both alternate email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vendor = Vendor.objects.get(alternate_email=alternate_email)
        except Vendor.DoesNotExist:
            return Response({"error": "Vendor with this alternate email not found."}, status=status.HTTP_404_NOT_FOUND)


        if vendor.otp != otp or now() > vendor.otp_expiry:
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        vendor.otp = None
        vendor.otp_expiry = None
        vendor.save()

        user = authenticate(request, username=vendor.email)

        if not user:
            return Response({"error": "Authentication failed."}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "OTP verified successfully. Logged in.",
            "id": user.id,
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]

class CategoryView(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class=CustomPageNumberPagination

from django_filters.rest_framework import DjangoFilterBackend
class CategoryListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = None

    def get_queryset(self):
        queryset = Category.objects.all()
        store_type_name = self.request.query_params.get('store_type_name')
        name = self.request.query_params.get('name')

        if store_type_name:
            queryset = queryset.filter(store_type__name__iexact=store_type_name)

        if name:
            queryset = queryset.filter(name__icontains=name)  # partial match, case-insensitive

        return queryset


class ApproveVendorUpdateView(APIView):
    def post(self, request, pk, *args, **kwargs):
        try:
            vendor = Vendor.objects.get(pk=pk)

            vendor.contact_number = vendor.pending_contact_number or vendor.contact_number
            vendor.fssai_certificate = vendor.pending_fssai_certificate or vendor.fssai_certificate
            vendor.license = vendor.pending_license or vendor.license

            vendor.pending_contact_number = None
            vendor.pending_fssai_certificate = None
            vendor.pending_license = None
            vendor.is_pending_update_approval = False
            vendor.save()

            return Response(
                {"message": "Vendor updates approved successfully."},
                status=status.HTTP_200_OK
            )
        except Vendor.DoesNotExist:
            return Response(
                {"error": "Vendor not found."},
                status=status.HTTP_404_NOT_FOUND
            )

class SubCategoryListView(APIView):
    def get(self, request):
        clothing_subcategories = ClothingSubCategory.objects.filter(is_active=True)
        grocery_subcategories = GrocerySubCategories.objects.filter(enable_subcategory=True)
        food_subcategories = FoodSubCategories.objects.filter(enable_subcategory=True)

        clothing_serializer = ClothingSubCategorySerializerlist(clothing_subcategories, many=True, context={'request': request})
        grocery_serializer = GrocerySubCategorySerializerlist(grocery_subcategories, many=True, context={'request': request})
        food_serializer = FoodSubCategorySerializerlist(food_subcategories, many=True, context={'request': request})

        data = {
            "clothing_subcategories": clothing_serializer.data,
            "grocery_subcategories": grocery_serializer.data,
            "food_subcategories": food_serializer.data,
        }
        return Response(data, status=status.HTTP_200_OK)


class VendorProductListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination

    def get_paginated_response(self, queryset, request, serializer_class):
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        if paginated_queryset is not None:
            serializer = serializer_class(paginated_queryset, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        serializer = serializer_class(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def get(self, request, vendor_id):
        # Check for vendor in Clothing
        if Clothing.objects.filter(vendor_id=vendor_id).exists():
            clothing_products = Clothing.objects.filter(
                vendor_id=vendor_id,
            ).select_related('category', 'subcategory', 'vendor').prefetch_related(
                'clothcolors__sizes', 'images'
            )
            
            # Add debug logging
            print(f"Found {clothing_products.count()} clothing products for vendor {vendor_id}")
            
            return self.get_paginated_response(clothing_products, request, ClothingSerializer)

        # Check for vendor in Dish
        elif Dish.objects.filter(vendor_id=vendor_id).exists():
            dish_products = Dish.objects.filter(
                vendor_id=vendor_id,
            ).select_related('category', 'subcategory', 'vendor').prefetch_related('images')
            
            # Add debug logging
            print(f"Found {dish_products.count()} dish products for vendor {vendor_id}")
            
            return self.get_paginated_response(dish_products, request, DishCreateSerializer)

        # Check for vendor in Grocery
        elif GroceryProducts.objects.filter(vendor_id=vendor_id).exists():
            grocery_products = GroceryProducts.objects.filter(
                vendor_id=vendor_id,
            ).select_related('category', 'subcategory', 'vendor').prefetch_related('images')
            
            # Add debug logging
            print(f"Found {grocery_products.count()} grocery products for vendor {vendor_id}")
            
            return self.get_paginated_response(grocery_products, request, GroceryProductSerializer)

        # If no match found
        return Response(
            {"detail": "No products found for the given vendor ID."},
            status=status.HTTP_404_NOT_FOUND
        )

# class ProductCreateAPIView(APIView):
#     permission_classes= [AllowAny]
#     def post(self, request, *args, **kwargs):
#         serializer = ProductSerializer(data=request.data)

#         if serializer.is_valid():
#             product = serializer.save()
#             return Response({"message": "Product created successfully!", "product_id": product.id}, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VendorProductsCountView(APIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, vendor_id):
        authenticated_vendor = request.user


        if authenticated_vendor.id != vendor_id:
            raise PermissionDenied("You are not authorized to access this vendor's data.")

        vendor = authenticated_vendor


        vendor_type = None
        product_count = 0

        if GroceryProducts.objects.filter(vendor=vendor).exists():
            vendor_type = "Grocery"
            product_count = GroceryProducts.objects.filter(vendor=vendor).count()
        elif Clothing.objects.filter(vendor=vendor).exists():
            vendor_type = "Clothing"
            product_count = Clothing.objects.filter(vendor=vendor).count()
        elif Dish.objects.filter(vendor=vendor).exists():
            vendor_type = "Dishes"
            product_count = Dish.objects.filter(vendor=vendor).count()

        if vendor_type:
            return Response({"vendor_type": vendor_type, "product_count": product_count})

        return Response({"error": "Vendor type not found"}, status=404)


class VendorAvailableProductsCountView(APIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, vendor_id):
        authenticated_vendor = request.user  # Vendor from token

        # Ensure the token's vendor ID matches the requested vendor_id
        if authenticated_vendor.id != vendor_id:
            raise PermissionDenied("You are not authorized to access this vendor's data.")

        vendor = authenticated_vendor  # Vendor is already fetched from token

        # Get counts of available products per category
        grocery_count = GroceryProducts.objects.filter(vendor=vendor, is_available=True).count()
        clothing_count = Clothing.objects.filter(vendor=vendor, is_available=True).count()
        dishes_count = Dish.objects.filter(vendor=vendor, is_available=True).count()

        total_count = grocery_count + clothing_count + dishes_count

        return Response({
            "vendor_id":vendor.id,
            "available_product_count": total_count
        })


def get_vendor_out_of_stock_counts(vendor_id):
    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        return {
            'error': 'Vendor not found'
        }

    # Initialize counts
    counts = {
        'clothing': 0,
        'grocery': 0,
        'food': 0,
        'total': 0
    }

    clothing_items = Clothing.objects.filter(vendor=vendor, is_active=True)
    for item in clothing_items:
        all_variants_out_of_stock = True

        for color in item.colors:
            for size in color.get('sizes', []):
                if size.get('stock', 0) > 0:
                    all_variants_out_of_stock = False
                    break
            if not all_variants_out_of_stock:
                break

        if all_variants_out_of_stock:
            counts['clothing'] += 1

    grocery_items = GroceryProducts.objects.filter(vendor=vendor, is_available=True)
    for item in grocery_items:
        all_weights_out_of_stock = True

        if isinstance(item.weights, dict):
            for weight_data in item.weights.values():
                if weight_data.get('is_in_stock', False):
                    all_weights_out_of_stock = False
                    break
        elif isinstance(item.weights, list):
            for weight_data in item.weights:
                if weight_data.get('is_in_stock', False):
                    all_weights_out_of_stock = False
                    break

        if all_weights_out_of_stock:
            counts['grocery'] += 1

    # Count out-of-stock food dishes
    dish_items = Dish.objects.filter(vendor=vendor, is_available=True)
    for item in dish_items:
        all_variants_out_of_stock = True

        if isinstance(item.variants, dict):
            # Dictionary format
            for variant_data in item.variants.values():
                if variant_data.get('is_in_stock', False):
                    all_variants_out_of_stock = False
                    break
        elif isinstance(item.variants, list):
            # List format
            for variant_data in item.variants:
                if variant_data.get('is_in_stock', False):
                    all_variants_out_of_stock = False
                    break

        if all_variants_out_of_stock:
            counts['food'] += 1

    counts['total'] = counts['clothing'] + counts['grocery'] + counts['food']

    return counts

class VendorOutOfStockDetailView(APIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, vendor_id):
        authenticated_vendor = request.user

        if not (authenticated_vendor.id == vendor_id or authenticated_vendor.is_staff):
            return Response({
                'status': 'error',
                'message': 'You do not have permission to access this vendor\'s data'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Vendor not found'
            }, status=status.HTTP_404_NOT_FOUND)

        vendor_types = []
        if Dish.objects.filter(vendor=vendor).exists():
            vendor_types.append('food')
        if Clothing.objects.filter(vendor=vendor).exists():
            vendor_types.append('clothing')
        if GroceryProducts.objects.filter(vendor=vendor).exists():
            vendor_types.append('grocery')

        counts = get_vendor_out_of_stock_counts(vendor.id)

        filtered_counts = {
            product_type: count
            for product_type, count in counts.items()
            if product_type in vendor_types or product_type == 'total'
        }

        return Response({
            'status': 'success',
            'data': {
                'vendor_name': vendor.business_name,
                'vendor_id': vendor.id,
                'vendor_types': vendor_types,
                'out_of_stock_counts': filtered_counts
            }
        }, status=status.HTTP_200_OK)

class VendorAnalyticsView(APIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_vendor_out_of_stock_counts(self, vendor):
        counts = {
            'clothing': 0,
            'grocery': 0,
            'food': 0,
            'total': 0
        }

        # Clothing out-of-stock count
        clothing_items = Clothing.objects.filter(vendor=vendor, is_active=True)
        for item in clothing_items:
            all_variants_out_of_stock = all(
                all(size.get('stock', 0) == 0 for size in color.get('sizes', []))
                for color in item.colors
            )
            if all_variants_out_of_stock:
                counts['clothing'] += 1

        # Grocery out-of-stock count
        grocery_items = GroceryProducts.objects.filter(vendor=vendor, is_available=True)
        for item in grocery_items:
            all_weights_out_of_stock = all(
                weight_data.get('is_in_stock', False) is False
                for weight_data in (item.weights if isinstance(item.weights, list) else item.weights.values())
            )
            if all_weights_out_of_stock:
                counts['grocery'] += 1

        # Dish out-of-stock count
        dish_items = Dish.objects.filter(vendor=vendor, is_available=True)
        for item in dish_items:
            all_variants_out_of_stock = all(
                variant_data.get('is_in_stock', False) is False
                for variant_data in (item.variants if isinstance(item.variants, list) else item.variants.values())
            )
            if all_variants_out_of_stock:
                counts['food'] += 1

        # Total out-of-stock count
        counts['total'] = counts['clothing'] + counts['grocery'] + counts['food']
        return counts

    def get(self, request, vendor_id):
        authenticated_vendor = request.user

        if authenticated_vendor.id != vendor_id:
            raise PermissionDenied("You are not authorized to access this vendor's data.")

        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response({"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND)

        # Determine vendor type(s)
        vendor_types = []
        if Dish.objects.filter(vendor=vendor).exists():
            vendor_types.append('food')
        if Clothing.objects.filter(vendor=vendor).exists():
            vendor_types.append('clothing')
        if GroceryProducts.objects.filter(vendor=vendor).exists():
            vendor_types.append('grocery')

        # Get total product count
        total_product_count = (
            GroceryProducts.objects.filter(vendor=vendor).count() +
            Clothing.objects.filter(vendor=vendor).count() +
            Dish.objects.filter(vendor=vendor).count()
        )

        # Get available product count
        available_product_count = (
            GroceryProducts.objects.filter(vendor=vendor, is_available=True).count() +
            Clothing.objects.filter(vendor=vendor, is_available=True).count() +
            Dish.objects.filter(vendor=vendor, is_available=True).count()
        )

        # Get out-of-stock product counts
        out_of_stock_counts = self.get_vendor_out_of_stock_counts(vendor)

        return Response({
            "vendor_id": vendor.id,
            "vendor_name": vendor.business_name,
            "vendor_types": vendor_types,
            "total_product_count": total_product_count,
            "available_product_count": available_product_count,
            "out_of_stock_counts": out_of_stock_counts
        }, status=status.HTTP_200_OK)

class CategorySearchAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'store_type__name']
    permission_classes=[AllowAny]


class SubCategoryListView(generics.ListAPIView):
    queryset = SubCategory.objects.filter(is_active=True).order_by('-id')
    serializer_class = SubCategorySerializer
    pagination_class = None

# Create subcategory (admin only)
class SubCategoryCreateView(generics.CreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAdminUser]

# Update/Delete subcategory (admin only)
class SubCategoryUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAdminUser]

#subcategories request
class SubCategoryRequestCreateView(generics.CreateAPIView):
    queryset = SubCategoryRequest.objects.all()
    serializer_class = SubCategoryRequestSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user)

class SubCategoryRequestListView(generics.ListAPIView):
    serializer_class = SubCategoryRequestSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return SubCategoryRequest.objects.filter(
        vendor=self.request.user,
        status='PENDING'
        ).order_by('-created_at')


class VendorSubCategoryRequestListView(generics.ListAPIView):
    serializer_class = SubCategoryRequestSerializer
    authentication_classes = [VendorJWTAuthentication]

    def get_queryset(self):
        return SubCategoryRequest.objects.filter(
        vendor=self.request.user,
        status='PENDING'
        ).order_by('-created_at')


class ApproveSubCategoryRequestView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, request_id):
        try:
            subcategory_request = SubCategoryRequest.objects.get(id=request_id)
            action = request.data.get("action")

            if action == "approve":
                existing = SubCategory.objects.filter(
                    category=subcategory_request.category,
                    name=subcategory_request.name
                ).first()

                if existing:
                    subcategory_request.status = "APPROVED"
                    subcategory_request.save()
                    return Response(
                        {"message": "SubCategory already exists. Request marked as approved."},
                        status=status.HTTP_200_OK
                    )

                SubCategory.objects.create(
                    category=subcategory_request.category,
                    name=subcategory_request.name,
                    sub_category_image=subcategory_request.sub_category_image
                )
                subcategory_request.delete()
                return Response(
                    {"message": "SubCategory approved and created successfully."},
                    status=status.HTTP_200_OK
                )

            elif action == "reject":
                subcategory_request.delete()
                return Response(
                    {"message": "SubCategory request rejected."},
                    status=status.HTTP_200_OK
                )

            else:
                return Response(
                    {"error": "Invalid action."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except SubCategoryRequest.DoesNotExist:
            return Response(
                {"error": "SubCategoryRequest not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        except IntegrityError:
            return Response(
                {"error": "A SubCategory with this name already exists for the selected category."},
                status=status.HTTP_400_BAD_REQUEST
            )


class SubCategoryRequestListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubCategoryRequestSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get("status")

        queryset = SubCategoryRequest.objects.all().order_by("-id")

        if status_filter == "pending":
            queryset = queryset.filter(is_approved__isnull=True)
        elif status_filter == "approved":
            queryset = queryset.filter(is_approved=True)
        elif status_filter == "rejected":
            queryset = queryset.filter(is_approved=False)

        return queryset


class SubCategoryListByCategory(generics.ListAPIView):
    serializer_class = SubCategorySerializer
    pagination_class = CustomPageNumberPagination
    authentication_classes = [VendorJWTAuthentication]

    def get_queryset(self):
        category_id = self.kwargs['category_id']


        if not Category.objects.filter(id=category_id).exists():
            raise PermissionDenied("Category does not exist.")


        return SubCategory.objects.filter(
            category_id=category_id,
        )

class VendorSearchView(generics.ListAPIView):
    queryset = Vendor.objects.filter(is_active=True, is_approved=True)
    serializer_class = VendorSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['business_name', 'owner_name', 'city', 'store_id', 'business_location']

class NearbyVendorsAPIView(generics.ListAPIView):
    serializer_class = VendorDetailSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = []

    def get_queryset(self):
        latitude = self.request.query_params.get('latitude')
        longitude = self.request.query_params.get('longitude')

        if not latitude or not longitude:
            return Vendor.objects.none()

        try:
            user_lat = Decimal(latitude)
            user_long = Decimal(longitude)
        except InvalidOperation:
            return Vendor.objects.none()

        user_location = (user_lat, user_long)

        nearby_vendors = []
        for vendor in Vendor.objects.filter(latitude__isnull=False, longitude__isnull=False, is_approved=True):
            vendor_location = (vendor.latitude, vendor.longitude)
            dist = geopy_distance(user_location, vendor_location).km
            if dist <= 20:
                nearby_vendors.append(vendor.id)

        return Vendor.objects.filter(id__in=nearby_vendors)

    def list(self, request, *args, **kwargs):
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')

        if not latitude or not longitude:
            return Response(
                {"error": "Both latitude and longitude query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            Decimal(latitude)
            Decimal(longitude)
        except InvalidOperation:
            return Response(
                {"error": "Invalid latitude or longitude values."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().list(request, *args, **kwargs)


class NearbyVendorCategoriesOnlyAPIView(generics.ListAPIView):
    permission_classes=[]
    serializer_class = CategorySerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        latitude = self.request.query_params.get('latitude')
        longitude = self.request.query_params.get('longitude')

        if not latitude or not longitude:
            return Category.objects.none()

        user_location = (float(latitude), float(longitude))

        nearby_vendors = []
        for vendor in Vendor.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True):
            vendor_location = (float(vendor.latitude), float(vendor.longitude))
            distance_km = geodesic(user_location, vendor_location).km
            if distance_km <= 20:
                nearby_vendors.append(vendor.id)

        grocery_cats = GroceryProducts.objects.filter(vendor_id__in=nearby_vendors).values_list('category_id', flat=True)
        dish_cats = Dish.objects.filter(vendor_id__in=nearby_vendors).values_list('category_id', flat=True)
        clothing_cats = Clothing.objects.filter(vendor_id__in=nearby_vendors).values_list('category_id', flat=True)

        all_category_ids = set(grocery_cats) | set(dish_cats) | set(clothing_cats)

        return Category.objects.filter(id__in=all_category_ids).distinct()

    def list(self, request, *args, **kwargs):
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')

        if not latitude or not longitude:
            return Response({"error": "Latitude and longitude are required."}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)

            # Modify the image field manually
            for item in serializer.data:
                category = queryset.get(id=item['id'])
                item['image'] = request.build_absolute_uri(category.category_image.url) if category.category_image else None

            return self.get_paginated_response(serializer.data)

        # Fallback: no pagination
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

from cart.models import CheckoutItem,Order
class VendorOrderAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes=[VendorJWTAuthentication]

    def get(self, request, vendor_id=None):
        vendors = Vendor.objects.filter(id=vendor_id) if vendor_id else Vendor.objects.all()
        analytics = []

        for vendor in vendors:
            items = CheckoutItem.objects.filter(vendor=vendor).select_related('checkout')
            order_ids = items.values_list('checkout_id', flat=True).distinct()
            orders = Order.objects.filter(checkout_id__in=order_ids)

            analytics.append({
                'vendor_id': vendor.id,
                'vendor_name': vendor.business_name,
                'total_orders': orders.count(),
                'pending_orders': orders.filter(order_status='pending').count(),
                'delivered_orders': orders.filter(order_status='delivered').count(),
                'cancelled_orders': orders.filter(order_status='cancelled').count(),
                # 'total_revenue': orders.aggregate(total=Sum('final_amount'))['total'] or 0.00,
                # 'paid_orders': orders.filter(payment_status='paid').count(),
                # 'online_payments': orders.filter(payment_method='online').count(),
                # 'cod_payments': orders.filter(payment_method='cod').count(),
            })

        if vendor_id:
            return Response(analytics[0] if analytics else {"error": "No data found"}, status=200)
        return Response({'vendor_analytics': analytics}, status=200)

# List & Create
class AppCarouselListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    queryset = AppCarousel.objects.all()
    serializer_class = AppCarouselSerializer

    def get_queryset(self):
        vendor_id = self.request.query_params.get('vendor_id')
        if vendor_id:
            return self.queryset.filter(vendor_id=vendor_id)
        return self.queryset

# Retrieve, Update, Delete
class AppCarouselDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    queryset = AppCarousel.objects.all()
    serializer_class = AppCarouselSerializer


class AppCarouselListViewUser(generics.ListAPIView):
    permission_classes = []
    serializer_class = AppCarouselSerializer
    pagination_class = None
    queryset = AppCarousel.objects.all()

    def get_queryset(self):
        vendor_id = self.request.query_params.get('vendor_id')
        qs = super().get_queryset()
        if vendor_id:
            return qs.filter(vendor_id=vendor_id)
        return qs
    
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from django.db.models import Q, F
from math import radians, sin, cos, sqrt, atan2

class AdsCarouselListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AppCarouselSerializerByLoc
    pagination_class = None

    def get_queryset(self):
        queryset = AppCarouselByLocation.objects.filter(is_active=True)
        
        # Filter by vendor
        vendor_id = self.request.query_params.get('vendor_id')
        if vendor_id:
            try:
                vendor_id = int(vendor_id)
                queryset = queryset.filter(vendor_id=vendor_id)
            except ValueError:
                pass
        
        # Filter by location name
        location_search = self.request.query_params.get('location')
        if location_search:
            queryset = queryset.filter(
                Q(place_name__icontains=location_search)
            )
        
        # Filter carousels without vendor (platform ads)
        no_vendor = self.request.query_params.get('no_vendor')
        if no_vendor and no_vendor.lower() == 'true':
            queryset = queryset.filter(vendor__isnull=True)
        
        return queryset.select_related('vendor')

    def create(self, request, *args, **kwargs):
        # Vendor is now optional
        data = request.data.copy()
        
        # Validate required fields
        if not data.get('place_name'):
            return Response(
                {'error': 'place_name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdsCarouselDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AppCarouselSerializerByLoc
    queryset = AppCarouselByLocation.objects.all()


class UserCarouselByLocationView(generics.ListAPIView):
    """
    Get carousels for user based on their location
    """
    permission_classes = [AllowAny]
    serializer_class = AppCarouselSerializerByLoc
    pagination_class = None

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers using Haversine formula"""
        R = 6371  # Earth's radius in kilometers

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c

        return distance

    def get_queryset(self):
        user_lat = self.request.query_params.get('latitude')
        user_lon = self.request.query_params.get('longitude')

        queryset = AppCarouselByLocation.objects.filter(is_active=True)

        if user_lat and user_lon:
            try:
                user_lat = float(user_lat)
                user_lon = float(user_lon)
                
                # Filter and calculate distances
                relevant_carousels = []
                for carousel in queryset:
                    if carousel.latitude and carousel.longitude:
                        distance = self.calculate_distance(
                            user_lat, user_lon,
                            carousel.latitude, carousel.longitude
                        )
                        
                        # Check if user is within the carousel's radius
                        if carousel.radius_km == 0 or distance <= carousel.radius_km:
                            carousel.distance = round(distance, 2)
                            relevant_carousels.append(carousel)
                
                # Sort by distance
                relevant_carousels.sort(key=lambda x: x.distance)
                return relevant_carousels
                
            except (ValueError, TypeError):
                pass

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class AdsCarouselListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AppCarouselSerializerByLoc
    pagination_class = None

    def get_queryset(self):
        vendor_id = self.request.query_params.get('vendor_id')
        queryset = AppCarouselByLocation.objects.all()

        if vendor_id:
            try:
                vendor_id = int(vendor_id)
            except ValueError:
                return AppCarouselByLocation.objects.none()
            
            queryset = queryset.filter(vendor_id=vendor_id)

        return queryset

class AdsCarouselDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    queryset = AppCarouselByLocation.objects.all()
    serializer_class = AppCarouselSerializerByLoc
    lookup_field = "id"

class AdsCarouselListViewUserLoc(generics.ListAPIView):
    permission_classes = []
    serializer_class = AppCarouselSerializerByLoc
    pagination_class = None

    def get_queryset(self):
        user_lat = self.request.query_params.get('lat')
        user_lon = self.request.query_params.get('lon')

        if not user_lat or not user_lon:
            return AppCarouselByLocation.objects.none()

        try:
            user_lat = float(user_lat)
            user_lon = float(user_lon)
        except ValueError:
            return AppCarouselByLocation.objects.none()

        queryset = AppCarouselByLocation.objects.all()
        nearby_ads = []

        for ad in queryset:
            if ad.latitude and ad.longitude:
                distance = self.haversine(user_lat, user_lon, ad.latitude, ad.longitude)
                if distance <= 20:
                    ad.distance = round(distance, 2)
                    nearby_ads.append(ad)

        return nearby_ads

    def list(self, request, *args, **kwargs):
        user_lat = request.query_params.get('lat')
        user_lon = request.query_params.get('lon')

        if not user_lat or not user_lon:
            return Response(
                {"error": "Both 'lat' and 'lon' parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            float(user_lat)
            float(user_lon)
        except ValueError:
            return Response(
                {"error": "Invalid 'lat' or 'lon' values."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().list(request, *args, **kwargs)

    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c


from django.utils import timezone
import pytz

class VendorByCategoryLocationView(APIView):
    permission_classes = []
    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        try:
            user_lat = float(request.query_params.get("lat"))
            user_lon = float(request.query_params.get("lon"))
        except (TypeError, ValueError):
            return Response(
                {"error": "lat and lon query parameters are required and must be numbers."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if abs(user_lat) > 90 or abs(user_lon) > 180:
            user_lat = user_lat / 10000.0
            user_lon = user_lon / 10000.0
        if not (-90 <= user_lat <= 90 and -180 <= user_lon <= 180):
            return Response({"error": "Invalid latitude/longitude values."}, status=400)

        vendors = Vendor.objects.filter(
            store_type=category.store_type,
            is_approved=True
        ).exclude(latitude__isnull=True, longitude__isnull=True)

        user_favourites = set()
        if request.user.is_authenticated:
            user_favourites = set(
                FavoriteVendor.objects.filter(user=request.user)
                .values_list('vendor_id', flat=True)
            )

        vendor_list = []
        kolkata_tz = pytz.timezone('Asia/Kolkata')

        for vendor in vendors:
            try:
                v_lat = float(vendor.latitude)
                v_lon = float(vendor.longitude)
            except (TypeError, ValueError):
                continue
            if not (-90 <= v_lat <= 90 and -180 <= v_lon <= 180):
                continue

            distance = self.haversine(user_lat, user_lon, v_lat, v_lon)
            if distance <= 16:
                opening_time_str = None
                closing_time_str = None

                if vendor.opening_time:
                    today = timezone.now().date()
                    opening_datetime = timezone.datetime.combine(today, vendor.opening_time)
                    opening_datetime = timezone.make_aware(opening_datetime, kolkata_tz)
                    opening_time_str = opening_datetime.strftime('%I:%M %p')

                if vendor.closing_time:
                    today = timezone.now().date()
                    closing_datetime = timezone.datetime.combine(today, vendor.closing_time)
                    closing_datetime = timezone.make_aware(closing_datetime, kolkata_tz)
                    closing_time_str = closing_datetime.strftime('%I:%M %p')

                is_favourite = vendor.id in user_favourites if request.user.is_authenticated else False

                vendor_list.append({
                    "id": vendor.id,
                    "business_name": vendor.business_name,
                    "owner_name": vendor.owner_name,
                    "store_logo": request.build_absolute_uri(vendor.store_logo.url) if vendor.store_logo else None,
                    "address": vendor.address,
                    "city": vendor.city,
                    "state": vendor.state,
                    "pincode": vendor.pincode,
                    "distance_km": round(distance, 2),
                    "opening_time": opening_time_str,
                    "closing_time": closing_time_str,
                    "is_favourite": is_favourite
                })

        vendor_list.sort(key=lambda x: x["distance_km"])
        return Response(vendor_list)

    def haversine(self, lat1, lon1, lat2, lon2):
        from math import radians, sin, cos, sqrt, atan2
        R = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

# List + Create (Admin or Vendor)
class VendorVideoListCreateView(generics.ListCreateAPIView):
    queryset = VendorVideo.objects.all()
    serializer_class = VendorVideoSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def get_queryset(self):
        vendor_id = self.request.query_params.get("vendor_id")
        if vendor_id:
            return self.queryset.filter(vendor_id=vendor_id, is_active=True)
        return self.queryset.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save()


class VendorVideoListViewAdmin(generics.ListCreateAPIView):
    queryset = VendorVideo.objects.all()
    serializer_class = VendorVideoSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        vendor_id = self.request.query_params.get("vendor_id")
        if vendor_id:
            return self.queryset.filter(vendor_id=vendor_id, is_active=True)
        return self.queryset.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save()


# Retrieve + Update + Delete (Admin/Vendor only)
class VendorVideoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VendorVideo.objects.all()
    serializer_class = VendorVideoSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

class VendorVideoDetailViewAdmin(generics.RetrieveUpdateDestroyAPIView):
    queryset = VendorVideo.objects.all()
    serializer_class = VendorVideoSerializer
    permission_classes = [IsAdminUser]


class VendorVideoListView(generics.ListAPIView):
    serializer_class = VendorVideoSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        latitude = self.request.query_params.get("latitude")
        longitude = self.request.query_params.get("longitude")
        vendor_id = self.request.query_params.get("vendor_id")

        qs = VendorVideo.objects.filter(is_active=True)

        if vendor_id:
            return qs.filter(vendor_id=vendor_id)

        if not latitude or not longitude:
            return VendorVideo.objects.none()

        user_location = (float(latitude), float(longitude))
        nearby_vendors = []

        for vendor in Vendor.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True):
            vendor_location = (float(vendor.latitude), float(vendor.longitude))
            distance_km = geodesic(user_location, vendor_location).km
            if distance_km <= 10:
                nearby_vendors.append(vendor.id)

        return qs.filter(vendor_id__in=nearby_vendors)

    def list(self, request, *args, **kwargs):
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")
        vendor_id = request.query_params.get("vendor_id")

        if not vendor_id and (not latitude or not longitude):
            return Response(
                {"error": "Either vendor_id or latitude/longitude is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

# ---------------------------------------------------------------------------------------------------------------------
#list only stories for 24 hrs

# class VendorVideoListView(generics.ListAPIView):
#     serializer_class = VendorVideoSerializer
#     permission_classes = [AllowAny]
#     pagination_class = None

#     def get_queryset(self):
#         vendor_id = self.request.query_params.get("vendor_id")
#         last_24_hours = timezone.now() - timedelta(hours=24)

#         qs = VendorVideo.objects.filter(is_active=True, created_at__gte=last_24_hours)
#         if vendor_id:
#             qs = qs.filter(vendor_id=vendor_id)
#         return qs

# ---------------------------------------------------------------------------------------
#delt by 48 hrs and show only for 24 hrs

# class VendorVideoListView(generics.ListAPIView):
#     serializer_class = VendorVideoSerializer
#     permission_classes = [AllowAny]
#     pagination_class = None

#     def get_queryset(self):
#         vendor_id = self.request.query_params.get("vendor_id")
#         now = timezone.now()

#         # Delete videos older than 48 hours
#         VendorVideo.objects.filter(created_at__lt=now - timedelta(hours=48)).delete()

#         # Show only last 24 hours
#         qs = VendorVideo.objects.filter(is_active=True, created_at__gte=now - timedelta(hours=24))
#         if vendor_id:
#             qs = qs.filter(vendor_id=vendor_id)
#         return qs

# ------------------------------------------------------------------------------------------------------------------------------
class VendorProductsView(APIView):
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination

    def get(self, request, vendor_id):
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response({"error": "Vendor not found"}, status=404)

        queryset = None
        serializer_class = None
        store_type = None

        if vendor.is_restaurent:
            queryset = Dish.objects.filter(
                vendor=vendor
            ).select_related('category', 'subcategory', 'vendor').prefetch_related('images')
            serializer_class = DishCreateSerializer
            store_type = "restaurant"

        elif vendor.is_Grocery:
            queryset = GroceryProducts.objects.filter(
                vendor=vendor
            ).select_related('category', 'subcategory', 'vendor').prefetch_related('images')
            serializer_class = GroceryProductSerializer
            store_type = "grocery"

        elif vendor.is_fashion:
            queryset = Clothing.objects.filter(
                vendor=vendor
            ).select_related('category', 'subcategory', 'vendor').prefetch_related(
                'clothcolors__sizes', 'images'
            )
            serializer_class = ClothingSerializer
            store_type = "fashion"

        else:
            return Response({"error": "Vendor store type not defined"}, status=400)
        
        vendor_data = VendorSerializer(vendor, context={"request": request}).data

        # Paginate the queryset
        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        
        # Serialize the paginated data
        serializer = serializer_class(paginated_qs, many=True, context={"request": request})
        
        # Create custom response with pagination metadata
        response_data = paginator.get_paginated_response(serializer.data)
        
        # Modify the response to include vendor and store_type
        response_data.data['results'] = {
            "store_type": store_type,
            "products": response_data.data['results'],  # Move the serialized data to 'products'
            "vendor": vendor_data,
        }
        
        return response_data

class NearbyRestaurantsAPIView(generics.ListAPIView):
    serializer_class = VendorDetailSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        latitude = self.request.query_params.get("latitude")
        longitude = self.request.query_params.get("longitude")

        if not latitude or not longitude:
            return Vendor.objects.none()

        try:
            user_lat = Decimal(latitude)
            user_long = Decimal(longitude)
        except InvalidOperation:
            return Vendor.objects.none()

        user_location = (user_lat, user_long)

        nearby_restaurants = []
        for vendor in Vendor.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            is_restaurent=True,
        ):
            vendor_location = (vendor.latitude, vendor.longitude)
            dist = geopy_distance(user_location, vendor_location).km
            if dist <= 20:
                nearby_restaurants.append(vendor.id)

        return Vendor.objects.filter(id__in=nearby_restaurants)

    def list(self, request, *args, **kwargs):
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")

        if not latitude or not longitude:
            return Response(
                {"error": "Both latitude and longitude query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            Decimal(latitude)
            Decimal(longitude)
        except InvalidOperation:
            return Response(
                {"error": "Invalid latitude or longitude values."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().list(request, *args, **kwargs)



class VendorCommissionAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        today = timezone.now().date()

        # Get all paid checkout items
        paid_items = CheckoutItem.objects.filter(
            checkout__order__payment_status="paid"
        ).select_related("vendor", "checkout__order")

        # Vendors who have sales today
        vendors = Vendor.objects.filter(
            id__in=paid_items.values_list("vendor_id", flat=True)
        )

        for vendor in vendors:
            # Calculate today's sales for this vendor
            total_sales = paid_items.filter(vendor=vendor).aggregate(
                total=Sum(F("price") * F("quantity"))
            )["total"] or Decimal("0.00")

            commission_percentage = vendor.commission or Decimal("0.00")
            commission_amount = (total_sales * commission_percentage) / Decimal("100")

            # Check if record already exists for today
            commission_record = VendorCommission.objects.filter(
                vendor=vendor,
                created_at__date=today
            ).first()

            if commission_record:
                commission_record.total_sales = total_sales
                commission_record.commission_percentage = commission_percentage
                commission_record.commission_amount = commission_amount

                if commission_record.payment_status == "pending" and commission_amount > 0:
                    commission_record.payment_status = "pending"

                commission_record.save()
            else:
                commission_record = VendorCommission.objects.create(
                    vendor=vendor,
                    total_sales=total_sales,
                    commission_percentage=commission_percentage,
                    commission_amount=commission_amount,
                    payment_status="pending"
                )

        commissions = VendorCommission.objects.filter(
            created_at__date=today
        ).select_related("vendor")

        serializer = VendorCommissionSerializer(
            commissions, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):

        commission_id = request.data.get("commission_id")
        payment_status = request.data.get("payment_status")

        if not commission_id or not payment_status:
            return Response(
                {"detail": "commission_id and payment_status are required"},
                status=400
            )

        try:
            commission = VendorCommission.objects.get(id=commission_id)
        except VendorCommission.DoesNotExist:
            return Response({"detail": "Commission not found"}, status=404)

        if payment_status not in dict(VendorCommission.PAYMENT_STATUS_CHOICES):
            return Response({"detail": "Invalid payment status"}, status=400)

        commission.payment_status = payment_status

        if payment_status == "paid":
            commission.paid_at = timezone.now()
        else:
            commission.paid_at = None

        commission.save()

        return Response({"detail": "Payment status updated successfully"})


