from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer, UserDeviceSerializer, AdminNotificationSendSerializer
from .services import NotificationService
from users.models import UserDevice, User

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
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
        if serializer.is_valid():
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
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
