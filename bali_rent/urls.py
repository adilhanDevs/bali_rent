from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import (
    UserViewSet, ProfileView, RegisterView, LogoutView, 
    PasswordResetView, PasswordResetConfirmView, LoginView
)
from catalog.views import VehicleTypeViewSet, VehicleModelViewSet, VehicleViewSet
from addons.api_base import AddonViewSet
from delivery.api_base import DeliveryZoneViewSet, DeliveryAddressViewSet
from bookings.views import BookingViewSet
from bookings.api_base import AvailabilityBlockViewSet
from payments.api_base import PaymentViewSet
from crypto_payments.views import CryptoWebhookView
from analytics.views import (
    AnalyticsEventCreateView, AdminAnalyticsRevenueView, AdminAnalyticsFunnelView
)
from pricing.views import (
    AdminSeasonViewSet, AdminScooterSeasonPriceViewSet,
    AdminOccupancyPricingRuleViewSet, AdminDevicePricingRuleViewSet,
    AdminGeoPricingRuleViewSet, AdminPriceCalculationLogViewSet
)
from marketing.views import (
    AdminPromotionCampaignViewSet, AdminPromoCodeViewSet, AdminBannerViewSet, BannerViewSet
)
from audit.views import (
    AdminAuditLogViewSet, AdminSecurityLoginLogViewSet, AdminSecurityWebhookLogViewSet
)
from documents.views import UserDocumentViewSet, AdminDocumentViewSet
from notifications.api_base import NotificationViewSet, UserDeviceRegistrationView, AdminNotificationSendView
from reviews.views import ReviewViewSet, AdminReviewViewSet
from bali_rent.public_views import PublicSiteBootstrapView

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

# Banners (Dev 1)
router.register(r'banners', BannerViewSet, basename='banner')

# Admin
from bali_rent.admin_api import AdminScooterViewSet, AdminScooterImageViewSet, AdminBookingViewSet, AdminUserViewSet, AdminFAQItemViewSet
from news.views import NewsArticleViewSet, AdminNewsArticleViewSet

# News
router.register(r'news', NewsArticleViewSet, basename='news')
admin_router = DefaultRouter()
admin_router.register(r'scooters', AdminScooterViewSet, basename='admin-scooter')
admin_router.register(r'scooter-images', AdminScooterImageViewSet, basename='admin-scooter-image')
admin_router.register(r'bookings', AdminBookingViewSet, basename='admin-booking')
admin_router.register(r'users', AdminUserViewSet, basename='admin-user')
admin_router.register(r'documents', AdminDocumentViewSet, basename='admin-document')
admin_router.register(r'reviews', AdminReviewViewSet, basename='admin-review')
admin_router.register(r'audit', AdminAuditLogViewSet, basename='admin-audit')
admin_router.register(r'security/logins', AdminSecurityLoginLogViewSet, basename='admin-security-logins')
admin_router.register(r'security/webhooks', AdminSecurityWebhookLogViewSet, basename='admin-security-webhooks')

# Pricing Admin
admin_router.register(r'pricing/seasons', AdminSeasonViewSet, basename='admin-season')
admin_router.register(r'pricing/scooter-prices', AdminScooterSeasonPriceViewSet, basename='admin-scooter-season-price')
admin_router.register(r'pricing/occupancy-rules', AdminOccupancyPricingRuleViewSet, basename='admin-occupancy-rule')
admin_router.register(r'pricing/device-rules', AdminDevicePricingRuleViewSet, basename='admin-device-rule')
admin_router.register(r'pricing/geo-rules', AdminGeoPricingRuleViewSet, basename='admin-geo-rule')
admin_router.register(r'pricing/calculation-logs', AdminPriceCalculationLogViewSet, basename='admin-price-log')

# Marketing Admin
admin_router.register(r'marketing/campaigns', AdminPromotionCampaignViewSet, basename='admin-campaign')
admin_router.register(r'marketing/promocodes', AdminPromoCodeViewSet, basename='admin-promocode')
admin_router.register(r'marketing/banners', AdminBannerViewSet, basename='admin-banner')

# Content Admin
admin_router.register(r'content/faq', AdminFAQItemViewSet, basename='admin-faq')
admin_router.register(r'content/news', AdminNewsArticleViewSet, basename='admin-news')

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # API v1
    path('api/v1/', include([
        path('public/bootstrap/', PublicSiteBootstrapView.as_view(), name='public-bootstrap'),
        # Auth
        path('auth/register/', RegisterView.as_view(), name='auth_register'),
        path('auth/login/', LoginView.as_view(), name='token_obtain_pair'),
        path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
        path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        path('auth/password-reset/', PasswordResetView.as_view(), name='password_reset'),
        path('auth/password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
        
        # Profile
        path('profile/', ProfileView.as_view(), name='profile'),
        
        # Specific subpaths (must be before router.urls)
        path('notifications/register-device/', UserDeviceRegistrationView.as_view(), name='register-device'),
        path('payments/', include('payments.urls')),
        path('payments/crypto/', include('crypto_payments.urls')),

        # Marketing
        path('marketing/', include('marketing.urls')),
        path('pricing/', include('pricing.urls')),
        path('delivery/calculate/', DeliveryZoneViewSet.as_view({'post': 'calculate'}), name='delivery_calculate'),
        path('analytics/events/', AnalyticsEventCreateView.as_view(), name='analytics-events'),
        
        # Webhooks
        path('webhooks/crypto/', include([
            path('<str:provider>/', include([
                path('', CryptoWebhookView.as_view(), name='crypto-webhook'),
            ])),
        ])),

        # Admin specific (non-router)
        path('admin/notifications/send/', AdminNotificationSendView.as_view(), name='admin-notification-send'),
        path('admin/analytics/revenue/', AdminAnalyticsRevenueView.as_view(), name='admin-analytics-revenue'),
        path('admin/analytics/funnel/', AdminAnalyticsFunnelView.as_view(), name='admin-analytics-funnel'),
        path('admin/crm/', include('crm.urls')),
        path('admin/tasks/', include('crm.task_urls')),
        
        # Loyalty & Chat (Dev 2, kept for compatibility as they were here)
        path('', include('loyalty.urls')),
        path('', include('chat.urls')),
        path('', include('support.urls')),
        
        # Admin Router
        path('admin/', include(admin_router.urls)),
        
        # Main Router
        path('', include(router.urls)),
    ])),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
