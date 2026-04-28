from django_filters import rest_framework as filters
from .models import Vehicle
from bookings.models import AvailabilityBlock
from django.db.models import Q

class VehicleFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name="base_price_usd", lookup_expr='gte')
    max_price = filters.NumberFilter(field_name="base_price_usd", lookup_expr='lte')
    type = filters.CharFilter(field_name="model__type__code")
    engine_capacity = filters.NumberFilter(field_name="model__engine_cc")
    start_date = filters.DateTimeFilter(method='filter_availability')
    end_date = filters.DateTimeFilter(method='filter_availability')

    class Meta:
        model = Vehicle
        fields = ['status', 'is_featured', 'model', 'type', 'engine_capacity']

    def filter_availability(self, queryset, name, value):
        start_date = self.data.get('start_date')
        end_date = self.data.get('end_date')

        if start_date and end_date:
            # Find vehicles that HAVE a block in this range
            blocked_vehicles = AvailabilityBlock.objects.filter(
                Q(start_at__lt=end_date) & Q(end_at__gt=start_date)
            ).values_list('vehicle_id', flat=True)
            
            # Exclude them
            return queryset.exclude(id__in=blocked_vehicles)
        
        return queryset
