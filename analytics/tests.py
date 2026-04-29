from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from users.models import User
from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .models import AnalyticsEvent

class AnalyticsAPITest(APITestCase):
    def setUp(self):
        self.url = reverse('analytics-events')
        self.user = User.objects.create_user(email='test@example.com', username='test', password='password')
        self.admin = User.objects.create_superuser(email='admin@example.com', username='admin', password='password', role='admin')
        self.manager = User.objects.create_user(email='manager@example.com', username='manager', password='password', role='manager')
        self.staff = User.objects.create_user(email='staff@example.com', username='staff', password='password', role='staff')
        self.client_user = User.objects.create_user(email='client@example.com', username='client', password='password', role='client')

        self.revenue_url = reverse('admin-analytics-revenue')
        self.funnel_url = reverse('admin-analytics-funnel')

        vehicle_type = VehicleType.objects.create(code='analytics-scooter', name='Analytics Scooter')
        vehicle_model = VehicleModel.objects.create(
            name='Click',
            brand='Honda',
            type=vehicle_type,
            engine_cc=125,
            transmission='auto',
            fuel_consumption=2.0,
            year=2024,
            trunk='small',
            helmets_count=2,
            description='Analytics test scooter',
            rental_terms='Standard',
        )
        self.vehicle = Vehicle.objects.create(
            model=vehicle_model,
            title='Honda Click',
            slug='honda-click-analytics',
            sku='ANL001',
            color='Blue',
            base_price_usd=Decimal('18.00'),
            status='available',
        )

    def test_anonymous_event_saved(self):
        payload = {"screen": "home", "action": "view"}
        response = self.client.post(self.url, {"event_name": "page_view", "payload": payload}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        self.assertEqual(event.event_name, "page_view")
        self.assertIsNone(event.user)

    def test_authenticated_event_saved(self):
        self.client.force_authenticate(user=self.user)
        payload = {"booking_id": 123}
        response = self.client.post(self.url, {"event_name": "start_checkout", "payload": payload}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = AnalyticsEvent.objects.first()
        self.assertEqual(event.user, self.user)

    def test_very_large_payload_rejected(self):
        # Create a payload > 10KB
        large_payload = {"data": "x" * 11000}
        response = self.client.post(self.url, {"event_name": "large_event", "payload": large_payload}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Payload too large", str(response.data['payload']))

    def test_admin_revenue_endpoint_returns_bookings_and_revenue(self):
        Booking.objects.create(
            public_number='BK-AN-1',
            user=self.client_user,
            vehicle=self.vehicle,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=2),
            payment_method='online_card',
            payment_status='paid',
            currency='USD',
            subtotal_usd=Decimal('50.00'),
            total_usd=Decimal('50.00'),
            total_display='USD 50.00',
            status='confirmed',
        )
        Booking.objects.create(
            public_number='BK-AN-2',
            user=self.client_user,
            vehicle=self.vehicle,
            start_at=timezone.now() + timedelta(days=3),
            end_at=timezone.now() + timedelta(days=4),
            payment_method='cash_on_delivery',
            payment_status='pending',
            currency='USD',
            subtotal_usd=Decimal('70.00'),
            total_usd=Decimal('70.00'),
            total_display='USD 70.00',
            status='confirmed',
        )
        Booking.objects.create(
            public_number='BK-AN-3',
            user=self.client_user,
            vehicle=self.vehicle,
            start_at=timezone.now() + timedelta(days=5),
            end_at=timezone.now() + timedelta(days=6),
            payment_method='online_card',
            payment_status='pending',
            currency='USD',
            subtotal_usd=Decimal('90.00'),
            total_usd=Decimal('90.00'),
            total_display='USD 90.00',
            status='cancelled',
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.revenue_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['bookings_count'], 2)
        self.assertEqual(Decimal(response.data['revenue']), Decimal('120.00'))
        self.assertEqual(response.data['currency'], 'USD')

    def test_admin_funnel_endpoint_returns_conversion(self):
        AnalyticsEvent.objects.create(event_name='page_view', payload={'screen': 'home'}, session_id='s1')
        AnalyticsEvent.objects.create(event_name='page_view', payload={'screen': 'catalog'}, session_id='s2')
        AnalyticsEvent.objects.create(event_name='page_view', payload={'screen': 'booking'}, session_id='s3')
        AnalyticsEvent.objects.create(event_name='start_checkout', payload={'step': 1}, session_id='s1')
        AnalyticsEvent.objects.create(event_name='start_checkout', payload={'step': 1}, session_id='s2')
        AnalyticsEvent.objects.create(event_name='booking_created', payload={'booking_id': 1}, session_id='s1')

        self.client.force_authenticate(user=self.manager)
        response = self.client.get(self.funnel_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['visitors'], 3)
        self.assertEqual(response.data['checkout_started'], 2)
        self.assertEqual(response.data['bookings_created'], 1)
        self.assertEqual(Decimal(response.data['conversion_rate']), Decimal('33.33'))
        self.assertEqual(Decimal(response.data['checkout_conversion_rate']), Decimal('50.00'))

    def test_staff_has_read_access_to_admin_analytics(self):
        self.client.force_authenticate(user=self.staff)
        revenue_response = self.client.get(self.revenue_url)
        funnel_response = self.client.get(self.funnel_url)

        self.assertEqual(revenue_response.status_code, status.HTTP_200_OK)
        self.assertEqual(funnel_response.status_code, status.HTTP_200_OK)

    def test_client_has_no_access_to_admin_analytics(self):
        self.client.force_authenticate(user=self.client_user)
        revenue_response = self.client.get(self.revenue_url)
        funnel_response = self.client.get(self.funnel_url)

        self.assertEqual(revenue_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(funnel_response.status_code, status.HTTP_403_FORBIDDEN)
