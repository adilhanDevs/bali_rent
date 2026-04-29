from django.utils import timezone
from rest_framework import permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from users.models import User, UserDevice

from .models import Notification
from .serializers import (
    AdminNotificationSendSerializer,
    NotificationSerializer,
    UserDeviceSerializer,
)
from .services import NotificationService

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_read', 'type']
    search_fields = ['title', 'body', 'type']
    ordering_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='read', url_name='read')
    def read(self, request, pk=None):
        notification = self.get_object()
        NotificationService.mark_as_read(notification)
        return Response({'status': 'marked as read'})

    @action(detail=True, methods=['post'], url_path='mark-read', url_name='mark-read')
    def mark_read(self, request, pk=None):
        return self.read(request, pk=pk)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({'status': 'all marked as read'})

class UserDeviceRegistrationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UserDeviceSerializer(data=request.data)
        if serializer.is_valid():
            fcm_token = serializer.validated_data['fcm_token']
            UserDevice.objects.update_or_create(
                fcm_token=fcm_token,
                defaults={
                    'user': request.user,
                    'platform': serializer.validated_data['platform'],
                    'device_id': serializer.validated_data['device_id'],
                    'app_version': serializer.validated_data['app_version'],
                    'is_active': True
                }
            )
            return Response({'status': 'device registered'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminNotificationSendView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = AdminNotificationSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = serializer.validated_data['target']
        title = serializer.validated_data['title']
        body = serializer.validated_data['body']
        notification_type = serializer.validated_data.get('type', 'admin_broadcast')
        data_json = serializer.validated_data.get('data_json')

        if target == 'user':
            user_id = serializer.validated_data.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                NotificationService.create_notification(user, title, body, notification_type, data_json)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        elif target == 'all':
            NotificationService.send_to_all(title, body, notification_type, data_json)
        elif target == 'segment':
            segment = serializer.validated_data.get('segment')
            NotificationService.send_to_segment(segment, title, body, notification_type, data_json)

        return Response({'status': 'notifications sent'}, status=status.HTTP_200_OK)
