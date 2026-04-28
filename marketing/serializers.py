from rest_framework import serializers
from .models import PromoCode, PromotionCampaign, Banner

# Public
class PromoCodeValidateSerializer(serializers.Serializer):
    code = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class PromoCodeResponseSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    code = serializers.CharField()
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.CharField(required=False, allow_null=True)

# Admin
class PromotionCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionCampaign
        fields = '__all__'

class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = '__all__'

class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = '__all__'
