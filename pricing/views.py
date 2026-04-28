from rest_framework import views, viewsets, response, status, permissions
from .serializers import (
    PricingCalculateSerializer, PricingResponseSerializer,
    SeasonSerializer, ScooterSeasonPriceSerializer,
    OccupancyPricingRuleSerializer, DevicePricingRuleSerializer,
    GeoPricingRuleSerializer, PriceCalculationLogSerializer
)
from .models import (
    Season, ScooterSeasonPrice, OccupancyPricingRule,
    DevicePricingRule, GeoPricingRule, PriceCalculationLog
)
from .services import PricingCalculationService

class PricingCalculateView(views.APIView):
    permission_classes = [permissions.AllowAny] # Usually pricing is public to see before booking

    def post(self, request):
        serializer = PricingCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Get client IP and User Agent for logging
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT')
        
        try:
            result = PricingCalculationService.calculate_full_price(
                vehicle_id=data['vehicle_id'],
                start_at=data['start_at'],
                end_at=data['end_at'],
                addon_ids=data.get('addon_ids'),
                delivery_lat=data.get('delivery_lat'),
                delivery_lng=data.get('delivery_lng'),
                promo_code=data.get('promo_code'),
                device_platform=data.get('device_platform'),
                user_country=data.get('user_country'),
                user=request.user if request.user.is_authenticated else None,
                ip_address=ip,
                user_agent=user_agent
            )
            return response.Response(PricingResponseSerializer(result).data)
        except Exception as e:
            return response.Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Admin ViewSets
from audit.mixins import AuditMixin

class AdminSeasonViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminScooterSeasonPriceViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = ScooterSeasonPrice.objects.all()
    serializer_class = ScooterSeasonPriceSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminOccupancyPricingRuleViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = OccupancyPricingRule.objects.all()
    serializer_class = OccupancyPricingRuleSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminDevicePricingRuleViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = DevicePricingRule.objects.all()
    serializer_class = DevicePricingRuleSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminGeoPricingRuleViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = GeoPricingRule.objects.all()
    serializer_class = GeoPricingRuleSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminPriceCalculationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PriceCalculationLog.objects.all()
    serializer_class = PriceCalculationLogSerializer
    permission_classes = [permissions.IsAdminUser]
