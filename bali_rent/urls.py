from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from users.views import (
    UserViewSet, ProfileView, RegisterView, LogoutView, 
    PasswordResetView, PasswordResetConfirmView
)
from catalog.views import VehicleTypeViewSet, VehicleModelViewSet, VehicleViewSet
from addons.api_base import AddonViewSet
from delivery.api_base import DeliveryZoneViewSet, DeliveryAddressViewSet
from bookings.views import BookingViewSet
from bookings.api_base import AvailabilityBlockViewSet
from payments.api_base import PaymentViewSet
from documents.views import UserDocumentViewSet, AdminDocumentViewSet
from notifications.api_base import NotificationViewSet, UserDeviceRegistrationView, AdminNotificationSendView
from reviews.views import ReviewViewSet, AdminReviewViewSet

router = DefaultRouter()
# Users
router.register(r'users', UserViewSet, basename='user')

# Catalog
router.register(r'scooter-types', VehicleTypeViewSet, basename='scooter-type')
router.register(r'scooter-models', VehicleModelViewSet, basename='scooter-model')
router.register(r'scooters', VehicleViewSet, basename='scooter')

# Add-ons
router.register(r'add-ons', AddonViewSet, basename='addon')

# Delivery
router.register(r'delivery-zones', DeliveryZoneViewSet, basename='delivery-zone')
router.register(r'delivery-addresses', DeliveryAddressViewSet, basename='delivery-address')

# Bookings
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'availability-calendar', AvailabilityBlockViewSet, basename='availability')

# Payments
router.register(r'payments', PaymentViewSet, basename='payment')

# Documents
router.register(r'documents', UserDocumentViewSet, basename='document')

# Notifications
router.register(r'notifications', NotificationViewSet, basename='notification')

# Reviews
router.register(r'reviews', ReviewViewSet, basename='review')

# Admin
from bali_rent.admin_api import AdminScooterViewSet, AdminScooterImageViewSet, AdminBookingViewSet, AdminUserViewSet
admin_router = DefaultRouter()
admin_router.register(r'scooters', AdminScooterViewSet, basename='admin-scooter')
admin_router.register(r'scooter-images', AdminScooterImageViewSet, basename='admin-scooter-image')
admin_router.register(r'bookings', AdminBookingViewSet, basename='admin-booking')
admin_router.register(r'users', AdminUserViewSet, basename='admin-user')
admin_router.register(r'documents', AdminDocumentViewSet, basename='admin-document')
admin_router.register(r'reviews', AdminReviewViewSet, basename='admin-review')

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # API v1
    path('api/v1/', include([
        # Notifications (must be before router.urls to avoid conflict)
        path('notifications/register-device/', UserDeviceRegistrationView.as_view(), name='register-device'),
        path('admin/notifications/send/', AdminNotificationSendView.as_view(), name='admin-notification-send'),
        
        path('', include(router.urls)),
        path('admin/', include(admin_router.urls)),
        
        # Auth
        path('auth/register/', RegisterView.as_view(), name='auth_register'),
        path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
        path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        path('auth/password-reset/', PasswordResetView.as_view(), name='password_reset'),
        path('auth/password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
        
        # Profile
        path('profile/', ProfileView.as_view(), name='profile'),
        
        # Payments
        path('payments/', include('payments.urls')),
        
        # Delivery
        path('delivery/calculate/', DeliveryZoneViewSet.as_view({'post': 'calculate'}), name='delivery_calculate'),
    ])),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
