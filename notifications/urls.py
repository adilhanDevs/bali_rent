from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, UserDeviceRegistrationView, AdminNotificationSendView

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('register-device/', UserDeviceRegistrationView.as_view(), name='register-device'),
    path('admin/send/', AdminNotificationSendView.as_view(), name='admin-notification-send'),
    path('', include(router.urls)),
]
