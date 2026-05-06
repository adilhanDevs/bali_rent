from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import DatabaseError
from .models import Addon
from bali_rent.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin
from audit.mixins import AuditMixin

class AddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Addon
        fields = '__all__'

class AddonViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Addon.objects.all()
    serializer_class = AddonSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return Addon.objects.all()
        return Addon.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except DatabaseError:
            return Response([])
