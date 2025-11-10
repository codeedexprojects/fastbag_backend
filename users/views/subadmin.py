from rest_framework.permissions import IsAdminUser
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from users.models import CustomUser
from users.serializers import *

# Create staff user (Admin-only)
class CreateStaffView(generics.CreateAPIView):
    serializer_class = CreateStaffUserSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class StaffListView(generics.ListAPIView):
    queryset = CustomUser.objects.filter(is_staff=True)
    serializer_class = CreateStaffUserSerializer
    permission_classes = [IsAdminUser]
    pagination_class=None

class StaffDetailView(generics.RetrieveAPIView):
    queryset = CustomUser.objects.filter(is_staff=True)
    serializer_class = CreateStaffUserSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'mobile_number'
    pagination_class = None

class StaffUpdateView(generics.UpdateAPIView):
    queryset = CustomUser.objects.filter(is_staff=True)
    serializer_class = CreateStaffUserSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'mobile_number'
    pagination_class=None

class StaffDeleteView(generics.DestroyAPIView):
    queryset = CustomUser.objects.filter(is_staff=True)
    permission_classes = [IsAdminUser]
    lookup_field = 'mobile_number'