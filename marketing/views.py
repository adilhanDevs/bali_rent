from rest_framework import views, viewsets, response, status, permissions
from .serializers import (
    PromoCodeValidateSerializer, PromoCodeResponseSerializer,
    PromoCodeSerializer, PromotionCampaignSerializer, BannerSerializer
)
from .models import PromoCode, PromotionCampaign, Banner
from .services import MarketingService
from decimal import Decimal

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
                'discount_amount': result,
                'reason': None
            })
        else:
            return response.Response({
                'valid': False,
                'code': code,
                'discount_amount': Decimal('0.00'),
                'reason': result # Error message from service
            })

# Admin ViewSets
from audit.mixins import AuditMixin

class AdminPromotionCampaignViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = PromotionCampaign.objects.all()
    serializer_class = PromotionCampaignSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminPromoCodeViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminBannerViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    permission_classes = [permissions.IsAdminUser]
