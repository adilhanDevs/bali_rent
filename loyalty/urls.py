from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomerLoyaltyAccountViewSet,
    LoyaltyProgramViewSet,
    LoyaltyTierViewSet,
    LoyaltyTransactionViewSet,
    ReferralCodeViewSet,
)

public_router = DefaultRouter()
public_router.register(r'loyalty/accounts', CustomerLoyaltyAccountViewSet, basename='loyalty-account')
public_router.register(r'loyalty/transactions', LoyaltyTransactionViewSet, basename='loyalty-transaction')
public_router.register(r'loyalty/referral-codes', ReferralCodeViewSet, basename='loyalty-referral-code')

admin_router = DefaultRouter()
admin_router.register(r'programs', LoyaltyProgramViewSet, basename='admin-loyalty-program')
admin_router.register(r'tiers', LoyaltyTierViewSet, basename='admin-loyalty-tier')

urlpatterns = [
    path('', include(public_router.urls)),
    path('admin/loyalty/', include(admin_router.urls)),
]
