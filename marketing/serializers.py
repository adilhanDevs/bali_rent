from rest_framework import serializers

from .models import Banner, PromoCode, PromoCodeRedemption, PromotionCampaign


class PromoCodeValidateSerializer(serializers.Serializer):
    code = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class PromoCodeResponseSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    code = serializers.CharField()
    discount = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    message = serializers.CharField()
    reason = serializers.CharField(required=False, allow_null=True)


class PromotionCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionCampaign
        fields = '__all__'


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = '__all__'


class PromoCodeRedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCodeRedemption
        fields = '__all__'
        read_only_fields = ('created_at',)


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = '__all__'
