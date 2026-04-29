from rest_framework import views, viewsets, response, status, permissions
from django.utils import timezone
from .serializers import (
    PromoCodeValidateSerializer, PromoCodeResponseSerializer,
    PromoCodeSerializer, PromotionCampaignSerializer, BannerSerializer
)
from .models import PromoCode, PromotionCampaign, Banner
from .services import MarketingService
from decimal import Decimal

class IsMarketingAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.role in {'admin', 'manager'}:
            return True
        if user.role == 'staff' and request.method in permissions.SAFE_METHODS:
            return True
        return False

class PromoCodeValidateView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PromoCodeValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        amount = serializer.validated_data['amount']
        
        promo, result = MarketingService.validate_promo_code(code, request.user, amount)
        
        if promo:
            return response.Response({
                'valid': True,
                'code': code,
                'discount': result,
                'discount_amount': result,
                'message': 'Promo code is valid',
                'reason': None
            })
        else:
            return response.Response({
                'valid': False,
                'code': code,
                'discount': Decimal('0.00'),
                'discount_amount': Decimal('0.00'),
                'message': result,
                'reason': result
            })

# Admin ViewSets
from audit.mixins import AuditMixin

class AdminPromotionCampaignViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = PromotionCampaign.objects.all()
    serializer_class = PromotionCampaignSerializer
    permission_classes = [IsMarketingAdmin]

class AdminPromoCodeViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    permission_classes = [IsMarketingAdmin]

class AdminBannerViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    permission_classes = [IsMarketingAdmin]

class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BannerSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        return Banner.objects.filter(
            is_active=True,
            starts_at__lte=now,
            ends_at__gte=now
        )
