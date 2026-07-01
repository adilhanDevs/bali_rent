from django_filters import rest_framework as filters
from .models import Vehicle
from django.db.models import Count, F, Q

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

        # This method backs both the start_date and end_date filters, so it runs twice when both
        # are supplied. Annotate only once to avoid a duplicate-alias error on the second pass.
        if '_availability_overlap' in queryset.query.annotations:
            return queryset

        if start_date and end_date:
            # A card represents `quantity` identical units, so keep it while at least one unit is
            # free: exclude only when overlapping blocks reach the card's quantity.
            return queryset.annotate(
                _availability_overlap=Count(
                    'availability_blocks',
                    filter=Q(
                        availability_blocks__start_at__lt=end_date,
                        availability_blocks__end_at__gt=start_date,
                    ),
                )
            ).filter(_availability_overlap__lt=F('quantity'))

        return queryset
