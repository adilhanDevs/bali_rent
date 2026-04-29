from decimal import Decimal

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, response, status, views, viewsets
from rest_framework.pagination import PageNumberPagination

from audit.mixins import AuditMixin

from .models import Banner, PromoCode, PromotionCampaign
from .serializers import (
    BannerSerializer,
    PromoCodeResponseSerializer,
    PromoCodeSerializer,
    PromoCodeValidateSerializer,
    PromotionCampaignSerializer,
)
from .services import MarketingService


class MarketingPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsMarketingAdminManagerOrStaffReadOnly(permissions.BasePermission):
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


class PromoCodeValidateView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PromoCodeValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code']
        amount = serializer.validated_data['amount']
        promo, result = MarketingService.validate_promo_code(code, request.user, amount)

        message = 'Promo code is valid' if promo else result
        payload = {
            'valid': bool(promo),
            'code': code,
            'discount': result if promo else Decimal('0.00'),
            'discount_amount': result if promo else Decimal('0.00'),
            'message': message,
            'reason': None if promo else result,
        }
        return response.Response(PromoCodeResponseSerializer(payload).data, status=status.HTTP_200_OK)


class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BannerSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = MarketingPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['placement']
    ordering_fields = ['priority', 'starts_at', 'created_at']

    def get_queryset(self):
        now = timezone.now()
        return Banner.objects.filter(
            is_active=True,
            starts_at__lte=now,
            ends_at__gte=now,
        )


class BaseMarketingAdminViewSet(AuditMixin, viewsets.ModelViewSet):
    permission_classes = [IsMarketingAdminManagerOrStaffReadOnly]
    pagination_class = MarketingPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class AdminPromotionCampaignViewSet(BaseMarketingAdminViewSet):
    queryset = PromotionCampaign.objects.all()
    serializer_class = PromotionCampaignSerializer
    filterset_fields = ['is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['starts_at', 'ends_at', 'name', 'code']


class AdminPromoCodeViewSet(BaseMarketingAdminViewSet):
    queryset = PromoCode.objects.select_related('campaign')
    serializer_class = PromoCodeSerializer
    filterset_fields = ['campaign', 'discount_type', 'is_active']
    search_fields = ['code', 'campaign__name', 'campaign__code']
    ordering_fields = ['code', 'usage_limit', 'current_usage', 'starts_at', 'ends_at']


class AdminBannerViewSet(BaseMarketingAdminViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    filterset_fields = ['placement', 'is_active']
    search_fields = ['title', 'placement', 'link_url']
    ordering_fields = ['priority', 'starts_at', 'ends_at', 'title']
