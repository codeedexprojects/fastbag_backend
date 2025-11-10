from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from users.models import UserRegNotification
from users.serializers import AdminNotificationSerializer
from rest_framework.permissions import IsAdminUser

class AdminNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = AdminNotificationSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['message', 'user__mobile_number']
    ordering_fields = ['created_at', 'is_read']
    ordering = ['-created_at']
    pagination_class  = None

    def get_queryset(self):
        return UserRegNotification.objects.all().select_related('user')

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = UserRegNotification.objects.filter(is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = UserRegNotification.objects.filter(is_read=False).update(is_read=True)
        return Response({'status': f'{updated} notifications marked read'})