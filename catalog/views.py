from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Exists, OuterRef
from django.db import DatabaseError
from .models import VehicleType, VehicleTypeTranslation, VehicleModel, Vehicle
from .serializers import (
    VehicleTypeSerializer, VehicleModelSerializer,
    ScooterListSerializer, ScooterDetailSerializer
)
from .filters import VehicleFilter
from bali_rent.permissions import IsAdminOrReadOnly
from bookings.models import AvailabilityBlock
from .services import get_vehicle_availability_calendar
from audit.mixins import AuditMixin

class VehicleTypeViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = VehicleType.objects.prefetch_related('translations').all()
    serializer_class = VehicleTypeSerializer
    permission_classes = [IsAdminOrReadOnly]

    @action(detail=True, methods=['get', 'post'], url_path='translations',
            permission_classes=[permissions.IsAdminUser])
    def translations(self, request, pk=None):
        vehicle_type = self.get_object()
        if request.method == 'GET':
            return Response([
                {'language': t.language, 'name': t.name}
                for t in vehicle_type.translations.all()
            ])
        data = request.data
        if not isinstance(data, list):
            return Response({'error': 'Expected a list of translation objects.'}, status=status.HTTP_400_BAD_REQUEST)
        for item in data:
            lang = (item.get('language') or '').strip()
            if not lang:
                continue
            VehicleTypeTranslation.objects.update_or_create(
                vehicle_type=vehicle_type,
                language=lang,
                defaults={
                    'name': (item.get('name') or '').strip() or vehicle_type.name,
                },
            )
        self._log_audit(vehicle_type, 'update_translations')
        return Response({'status': 'ok'})

class VehicleModelViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = VehicleModel.objects.select_related('type').prefetch_related('type__translations').all()
    serializer_class = VehicleModelSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['type']

from reviews.serializers import ReviewSerializer
from reviews.models import Review
from django.shortcuts import get_object_or_404

class VehicleViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = Vehicle.objects.filter(status='available').select_related('model__type').prefetch_related('images', 'translations')
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = VehicleFilter
    search_fields = ['title', 'model__name', 'model__brand']
    ordering_fields = ['base_price_usd', 'rating_avg', 'created_at']

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_value = self.kwargs.get(self.lookup_field or 'pk')

        if lookup_value is None:
            return super().get_object()

        # Support both numeric ids and canonical slugs for public frontend routes.
        if str(lookup_value).isdigit():
            return get_object_or_404(queryset, pk=lookup_value)
        return get_object_or_404(queryset, slug=lookup_value)

    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            conflicts = AvailabilityBlock.objects.filter(
                vehicle_id=OuterRef('pk'),
                start_at__lt=end_date,
                end_at__gt=start_date,
            )
            queryset = queryset.annotate(has_availability_conflict=Exists(conflicts))
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ScooterDetailSerializer
        return ScooterListSerializer

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except DatabaseError:
            # Keep the public storefront alive even when production DB schema/data
            # is temporarily out of sync. The frontend can fall back to local cards.
            return Response([])

    @action(detail=False, methods=['get'])
    def popular(self, request):
        try:
            queryset = self.get_queryset().filter(is_featured=True).order_by('-rating_avg')[:10]
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except DatabaseError:
            return Response([])

    @action(detail=True, methods=['get', 'post'], url_path='reviews', permission_classes=[permissions.AllowAny])
    def reviews(self, request, pk=None):
        scooter = self.get_object()
        if request.method == 'GET':
            reviews = scooter.reviews.filter(status='approved').select_related('user')
            serializer = ReviewSerializer(reviews, many=True, context={'request': request})
            return Response(serializer.data)
        
        if request.method == 'POST':
            if not request.user.is_authenticated:
                return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
            
            data = request.data.copy()
            data['scooter'] = scooter.id
            serializer = ReviewSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                review = serializer.save(user=request.user, status='pending')
                self._log_audit(review, 'create_review', after_dict=serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        vehicle = self.get_object()
        
        # Check for year/month for calendar view
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        if year and month:
            try:
                year = int(year)
                month = int(month)
                if not (1 <= month <= 12):
                    raise ValueError
                data = get_vehicle_availability_calendar(vehicle, year, month)
                return Response(data)
            except ValueError:
                return Response({"error": "Invalid year or month"}, status=status.HTTP_400_BAD_REQUEST)

        # Legacy start_date/end_date check
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date and end_date:
            is_available = not AvailabilityBlock.objects.filter(
                vehicle=vehicle,
                start_at__lt=end_date,
                end_at__gt=start_date
            ).exists()

            return Response({
                "vehicle_id": vehicle.id,
                "start_date": start_date,
                "end_date": end_date,
                "is_available": is_available
            })

        return Response({"error": "Please provide year/month or start_date/end_date"}, status=status.HTTP_400_BAD_REQUEST)
