from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import (
    CustomerLoyaltyAccount,
    LoyaltyProgram,
    LoyaltyTier,
    LoyaltyTransaction,
    ReferralCode,
)
from .serializers import (
    CustomerLoyaltyAccountSerializer,
    LoyaltyProgramSerializer,
    LoyaltyTierSerializer,
    LoyaltyTransactionSerializer,
    ReferralCodeSerializer,
)


class LoyaltyPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsLoyaltyAdminManagerOrStaffReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.role in {'admin', 'manager'}:
            return True
        if user.role == 'staff':
            return request.method in permissions.SAFE_METHODS
        return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class BaseLoyaltyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsLoyaltyAdminManagerOrStaffReadOnly]
    pagination_class = LoyaltyPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class LoyaltyProgramViewSet(BaseLoyaltyViewSet):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer
    search_fields = ['name']
    filterset_fields = ['is_active']
    ordering_fields = ['name']


class LoyaltyTierViewSet(BaseLoyaltyViewSet):
    queryset = LoyaltyTier.objects.select_related('program')
    serializer_class = LoyaltyTierSerializer
    search_fields = ['name', 'program__name']
    filterset_fields = ['program']
    ordering_fields = ['min_points', 'discount_percent', 'name']


class CustomerLoyaltyAccountViewSet(BaseLoyaltyViewSet):
    queryset = CustomerLoyaltyAccount.objects.select_related('customer', 'program', 'tier')
    serializer_class = CustomerLoyaltyAccountSerializer
    search_fields = ['customer__full_name', 'customer__email', 'customer__phone', 'program__name', 'tier__name']
    filterset_fields = ['program', 'tier']
    ordering_fields = ['points', 'customer__email', 'program__name']


class LoyaltyTransactionViewSet(BaseLoyaltyViewSet):
    queryset = LoyaltyTransaction.objects.select_related('account__customer', 'account__program', 'account__tier')
    serializer_class = LoyaltyTransactionSerializer
    search_fields = ['account__customer__full_name', 'account__customer__email', 'account__program__name']
    filterset_fields = ['account', 'type']
    ordering_fields = ['created_at', 'points']


class ReferralCodeViewSet(BaseLoyaltyViewSet):
    queryset = ReferralCode.objects.select_related('user')
    serializer_class = ReferralCodeSerializer
    search_fields = ['code', 'user__full_name', 'user__email', 'user__phone']
    filterset_fields = ['user']
    ordering_fields = ['created_at', 'code']
