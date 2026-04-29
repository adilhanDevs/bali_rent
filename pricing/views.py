from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, response, status, views, viewsets, throttling
from rest_framework.pagination import PageNumberPagination

from audit.mixins import AuditMixin

from .models import (
    DevicePricingRule,
    GeoPricingRule,
    OccupancyPricingRule,
    PriceCalculationLog,
    ScooterSeasonPrice,
    Season,
)
from .serializers import (
    DevicePricingRuleSerializer,
    GeoPricingRuleSerializer,
    OccupancyPricingRuleSerializer,
    PriceCalculationLogSerializer,
    PricingCalculateSerializer,
    PricingResponseSerializer,
    ScooterSeasonPriceSerializer,
    SeasonSerializer,
)
from .services import PricingCalculationService


class PricingPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsPricingAdminManagerOrStaffReadOnly(permissions.BasePermission):
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


class PricingCalculateView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = 'pricing_calculate'

    def post(self, request):
        serializer = PricingCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        result = PricingCalculationService.calculate_full_price(
            vehicle_id=data['scooter_id'],
            start_at=data['start_date'],
            end_at=data['end_date'],
            device_platform=data.get('device_type'),
            user_country=data.get('country_code'),
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
        return response.Response(PricingResponseSerializer(result).data, status=status.HTTP_200_OK)


class BasePricingAdminViewSet(AuditMixin, viewsets.ModelViewSet):
    permission_classes = [IsPricingAdminManagerOrStaffReadOnly]
    pagination_class = PricingPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class AdminSeasonViewSet(BasePricingAdminViewSet):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    filterset_fields = ['is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['start_date', 'end_date', 'name', 'code', 'multiplier']


class AdminScooterSeasonPriceViewSet(BasePricingAdminViewSet):
    queryset = ScooterSeasonPrice.objects.select_related('scooter', 'season')
    serializer_class = ScooterSeasonPriceSerializer
    filterset_fields = ['scooter', 'season']
    search_fields = ['scooter__title', 'scooter__sku', 'season__name', 'season__code']
    ordering_fields = ['price_per_day_usd', 'season__start_date', 'scooter__title']


class AdminOccupancyPricingRuleViewSet(BasePricingAdminViewSet):
    queryset = OccupancyPricingRule.objects.all()
    serializer_class = OccupancyPricingRuleSerializer
    filterset_fields = ['is_active']
    search_fields = ['=threshold_percent']
    ordering_fields = ['threshold_percent', 'price_increase_percent']


class AdminDevicePricingRuleViewSet(BasePricingAdminViewSet):
    queryset = DevicePricingRule.objects.all()
    serializer_class = DevicePricingRuleSerializer
    filterset_fields = ['device_type', 'country_code', 'is_active']
    search_fields = ['device_type', 'country_code']
    ordering_fields = ['device_type', 'country_code', 'multiplier']


class AdminGeoPricingRuleViewSet(BasePricingAdminViewSet):
    queryset = GeoPricingRule.objects.all()
    serializer_class = GeoPricingRuleSerializer
    filterset_fields = ['country_code', 'is_active']
    search_fields = ['country_code', 'city']
    ordering_fields = ['country_code', 'city', 'multiplier']


class AdminPriceCalculationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PriceCalculationLog.objects.select_related('booking', 'scooter', 'user')
    serializer_class = PriceCalculationLogSerializer
    permission_classes = [IsPricingAdminManagerOrStaffReadOnly]
    pagination_class = PricingPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['booking', 'scooter', 'user']
    search_fields = ['scooter__title', 'scooter__sku', 'user__email', 'user__full_name']
    ordering_fields = ['created_at', 'base_price', 'final_price']
