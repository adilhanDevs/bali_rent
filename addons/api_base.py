from rest_framework import serializers, viewsets, permissions
from .models import Addon
from bali_rent.permissions import IsAdminOrReadOnly

class AddonSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(source='price_usd', max_digits=10, decimal_places=2)

    class Meta:
        model = Addon
        fields = ('id', 'code', 'name', 'description', 'price', 'price_type', 
                  'is_active', 'sort_order', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

class AddonViewSet(viewsets.ModelViewSet):
    queryset = Addon.objects.all()
    serializer_class = AddonSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Addon.objects.all()
        return Addon.objects.filter(is_active=True)
