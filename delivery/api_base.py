from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DeliveryZone, DeliveryAddress
from bali_rent.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin
from .services import calculate_delivery_price

class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = '__all__'

class DeliveryCalculateSerializer(serializers.Serializer):
    address = serializers.CharField(required=False)
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    delivery_time = serializers.DateTimeField(required=False)

class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = '__all__'
        read_only_fields = ('user',)

class DeliveryZoneViewSet(viewsets.ModelViewSet):
    queryset = DeliveryZone.objects.all()
    serializer_class = DeliveryZoneSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return DeliveryZone.objects.all()
        return DeliveryZone.objects.filter(is_active=True)

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
            serializer.validated_data['longitude']
        )
        
        # If zone is in result, serialize it
        if result.get('zone'):
            result['zone'] = DeliveryZoneSerializer(result['zone']).data
            
        return Response(result)

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
