from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import DatabaseError
from .models import Addon, AddonTranslation
from bali_rent.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin
from audit.mixins import AuditMixin

class AddonSerializer(serializers.ModelSerializer):
    translations = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Addon
        fields = ['id', 'code', 'name', 'description', 'price_usd', 'price_type',
                  'is_active', 'sort_order', 'created_at', 'updated_at', 'translations']

    def get_translations(self, obj):
        return [
            {'language': t.language, 'name': t.name, 'description': t.description}
            for t in obj.translations.all()
        ]

class AddonViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Addon.objects.prefetch_related('translations').all()
    serializer_class = AddonSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        base = Addon.objects.prefetch_related('translations')
        if self.request.user and self.request.user.is_staff:
            return base.all()
        return base.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except DatabaseError:
            return Response([])

    @action(detail=True, methods=['get', 'post'], url_path='translations',
            permission_classes=[permissions.IsAdminUser])
    def translations(self, request, pk=None):
        addon = self.get_object()
        if request.method == 'GET':
            return Response([
                {'language': t.language, 'name': t.name, 'description': t.description}
                for t in addon.translations.all()
            ])
        data = request.data
        if not isinstance(data, list):
            return Response({'error': 'Expected a list of translation objects.'}, status=status.HTTP_400_BAD_REQUEST)
        for item in data:
            lang = (item.get('language') or '').strip()
            if not lang:
                continue
            AddonTranslation.objects.update_or_create(
                addon=addon,
                language=lang,
                defaults={
                    'name': (item.get('name') or '').strip() or addon.name,
                    'description': (item.get('description') or '').strip(),
                },
            )
        self._log_audit(addon, 'update_translations')
        return Response({'status': 'ok'})
