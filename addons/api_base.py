from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import DatabaseError
from django.db.models.deletion import ProtectedError
from django.utils.text import slugify
from .models import Addon, AddonTranslation
from bali_rent.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin
from audit.mixins import AuditMixin

class AddonSerializer(serializers.ModelSerializer):
    translations = serializers.SerializerMethodField(read_only=True)
    code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Addon
        fields = ['id', 'code', 'name', 'description', 'price_usd', 'price_type',
                  'is_active', 'sort_order', 'created_at', 'updated_at', 'translations']

    def get_translations(self, obj):
        return [
            {'language': t.language, 'name': t.name, 'description': t.description}
            for t in obj.translations.all()
        ]

    def _build_unique_code(self, name, instance=None):
        base_code = slugify(name).replace('-', '_') or 'addon'
        code = base_code
        counter = 2

        queryset = Addon.objects.all()
        if instance is not None:
            queryset = queryset.exclude(pk=instance.pk)

        while queryset.filter(code=code).exists():
            code = f'{base_code}_{counter}'
            counter += 1
        return code

    def validate(self, attrs):
        name = attrs.get('name') or getattr(self.instance, 'name', '')
        code = attrs.get('code')

        if not code and name:
            attrs['code'] = self._build_unique_code(name=name, instance=self.instance)

        return attrs

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

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'error': 'Cannot delete this add-on because it is already used in one or more bookings.'},
                status=status.HTTP_409_CONFLICT,
            )

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
