from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q, Sum

from bookings.models import Booking

from .models import AnalyticsEvent


TWOPLACES = Decimal('0.01')


class AnalyticsService:
    @staticmethod
    def track_event(user, event_name, properties=None, payload=None, ip_address=None, user_agent=None):
        event_payload = payload if payload is not None else (properties or {})
        return AnalyticsEvent.objects.create(
            user=user,
            event_name=event_name,
            payload=event_payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def _quantize(value):
        return Decimal(value or 0).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    def get_revenue_summary():
        revenue_bookings = Booking.objects.filter(
            Q(payment_status='paid') | Q(status__in=['confirmed', 'delivery', 'active', 'completed'])
        ).exclude(status='cancelled')

        bookings_count = revenue_bookings.count()
        revenue = revenue_bookings.aggregate(total=Sum('total_usd'))['total'] or Decimal('0.00')

        return {
            'bookings_count': bookings_count,
            'revenue': AnalyticsService._quantize(revenue),
            'currency': 'USD',
        }

    @staticmethod
    def _get_visitors_count():
        session_count = (
            AnalyticsEvent.objects.exclude(session_id__isnull=True)
            .exclude(session_id='')
            .values('session_id')
            .distinct()
            .count()
        )
        if session_count:
            return session_count

        device_count = (
            AnalyticsEvent.objects.exclude(device_id__isnull=True)
            .exclude(device_id='')
            .values('device_id')
            .distinct()
            .count()
        )
        if device_count:
            return device_count

        page_views = AnalyticsEvent.objects.filter(event_name='page_view').count()
        if page_views:
            return page_views

        auth_users = AnalyticsEvent.objects.exclude(user__isnull=True).values('user').distinct().count()
        if auth_users:
            return auth_users

        return AnalyticsEvent.objects.count()

    @staticmethod
    def get_funnel_summary():
        visitors = AnalyticsService._get_visitors_count()
        checkout_started = AnalyticsEvent.objects.filter(event_name='start_checkout').count()
        bookings_created = AnalyticsEvent.objects.filter(event_name='booking_created').count()
        if bookings_created == 0:
            bookings_created = Booking.objects.exclude(status='cancelled').count()

        conversion_rate = Decimal('0.00')
        checkout_conversion_rate = Decimal('0.00')
        if visitors:
            conversion_rate = AnalyticsService._quantize(
                (Decimal(bookings_created) / Decimal(visitors)) * Decimal('100')
            )
        if checkout_started:
            checkout_conversion_rate = AnalyticsService._quantize(
                (Decimal(bookings_created) / Decimal(checkout_started)) * Decimal('100')
            )

        return {
            'visitors': visitors,
            'checkout_started': checkout_started,
            'bookings_created': bookings_created,
            'conversion_rate': conversion_rate,
            'checkout_conversion_rate': checkout_conversion_rate,
        }
