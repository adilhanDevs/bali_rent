from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from bali_rent.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin

from .models import DeliveryAddress, DeliveryPoint, DeliveryPricingRule, DeliveryZone
from .services import calculate_delivery_price


class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = '__all__'


class DeliveryPricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPricingRule
        fields = '__all__'


class DeliveryPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPoint
        fields = '__all__'


class DeliveryCalculateSerializer(serializers.Serializer):
    address = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    lat = serializers.FloatField(required=False, write_only=True)
    lng = serializers.FloatField(required=False, write_only=True)
    delivery_time = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        latitude = attrs.get('latitude', attrs.get('lat'))
        longitude = attrs.get('longitude', attrs.get('lng'))
        if latitude is None:
            raise serializers.ValidationError({'latitude': 'This field is required.'})
        if longitude is None:
            raise serializers.ValidationError({'longitude': 'This field is required.'})
        attrs['latitude'] = latitude
        attrs['longitude'] = longitude
        return attrs


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = '__all__'
        read_only_fields = ('user',)


class DeliveryZoneViewSet(viewsets.ModelViewSet):
    queryset = DeliveryZone.objects.prefetch_related('pricing_rules')
    serializer_class = DeliveryZoneSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(is_active=True)

    def get_permissions(self):
        if self.action == 'calculate':
            return [permissions.AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        serializer = DeliveryCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = calculate_delivery_price(
            serializer.validated_data['latitude'],
            serializer.validated_data['longitude'],
        )

        zone = result.get('zone')
        if zone:
            result['zone_name'] = zone.name
            result['zone'] = DeliveryZoneSerializer(zone).data
        else:
            result['zone_name'] = None

        result['delivery_price'] = result['price']

        address = serializer.validated_data.get('address')
        if address:
            result['delivery_point'] = DeliveryPointSerializer(
                DeliveryPoint(
                    address=address,
                    lat=serializer.validated_data['latitude'],
                    lng=serializer.validated_data['longitude'],
                )
            ).data

        return Response(result, status=status.HTTP_200_OK)


class DeliveryPricingRuleViewSet(viewsets.ModelViewSet):
    queryset = DeliveryPricingRule.objects.select_related('zone')
    serializer_class = DeliveryPricingRuleSerializer
    permission_classes = [IsAdminOrReadOnly]


class DeliveryAddressViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAddress.objects.all()
    serializer_class = DeliveryAddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return DeliveryAddress.objects.all()
        return DeliveryAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
