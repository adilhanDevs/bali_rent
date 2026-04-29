from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType
from notifications.models import Notification, NotificationLog
from payments.models import Payment
from users.models import UserDevice

User = get_user_model()


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='password',
            username='user',
            role='client',
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='password',
            username='other',
            role='client',
        )
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password',
            username='admin',
            role='admin',
        )

        vehicle_type = VehicleType.objects.create(code='scooter', name='Scooter')
        vehicle_model = VehicleModel.objects.create(
            name='NMax',
            brand='Yamaha',
            type=vehicle_type,
            engine_cc=155,
            transmission='automatic',
            fuel_consumption=2.3,
            year=2024,
            trunk='medium',
            helmets_count=2,
            description='Good scooter',
            rental_terms='Standard terms',
        )
        self.vehicle = Vehicle.objects.create(
            model=vehicle_model,
            title='Yamaha NMax',
            slug='yamaha-nmax',
            sku='NMAX-001',
            color='Black',
            base_price_usd=Decimal('15.00'),
            status='available',
        )

    def create_booking(self, *, user=None, status='created', public_number='BK-TEST-001'):
        now = timezone.now()
        return Booking.objects.create(
            public_number=public_number,
            user=user or self.user,
            vehicle=self.vehicle,
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=3),
            payment_method='online_card',
            currency='USD',
            subtotal_usd=Decimal('100.00'),
            addons_total_usd=Decimal('0.00'),
            delivery_price_usd=Decimal('0.00'),
            discount_usd=Decimal('0.00'),
            markup_usd=Decimal('0.00'),
            total_usd=Decimal('100.00'),
            total_display='USD 100.00',
            status=status,
        )

    def create_payment(self, booking, status='pending'):
        return Payment.objects.create(
            booking=booking,
            provider='stripe',
            method='card',
            amount_usd=Decimal('100.00'),
            amount_display='USD 100.00',
            currency='USD',
            status=status,
            provider_payment_id=f'pay-{booking.id}-{status}',
        )

    def test_list_notifications_returns_only_current_user_items(self):
        Notification.objects.create(user=self.user, title='Mine', body='Body', type='manual')
        Notification.objects.create(user=self.other_user, title='Other', body='Body', type='manual')

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/notifications/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Mine')
        self.assertEqual(response.data['results'][0]['message'], 'Body')

    def test_read_endpoint_marks_notification_and_sets_read_at(self):
        notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            body='Test body',
            type='manual',
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/notifications/{notification.id}/read/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_mark_read_legacy_endpoint_still_works(self):
        notification = Notification.objects.create(
            user=self.user,
            title='Legacy Notification',
            body='Legacy body',
            type='manual',
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/notifications/{notification.id}/mark-read/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_user_cannot_mark_other_users_notification(self):
        notification = Notification.objects.create(
            user=self.other_user,
            title='Private',
            body='No access',
            type='manual',
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/notifications/{notification.id}/read/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_booking_created_signal_creates_notification_and_log(self):
        booking = self.create_booking(public_number='BK-CREATED-001')

        notification = Notification.objects.get(type='booking_created')
        log = NotificationLog.objects.get(event_type='booking_created')

        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.data_json['booking_id'], booking.id)
        self.assertEqual(log.notification, notification)
        self.assertEqual(log.event_key, f'booking-created:{booking.id}')
        self.assertEqual(log.status, 'sent')

    def test_booking_confirmed_signal_creates_single_notification(self):
        booking = self.create_booking(public_number='BK-CONFIRM-001')
        Notification.objects.all().delete()
        NotificationLog.objects.all().delete()

        booking.status = 'confirmed'
        booking.save()
        booking.save()

        self.assertEqual(Notification.objects.filter(type='booking_confirmed').count(), 1)
        self.assertEqual(NotificationLog.objects.filter(event_type='booking_confirmed').count(), 1)

        notification = Notification.objects.get(type='booking_confirmed')
        self.assertEqual(notification.data_json['public_number'], booking.public_number)

    def test_payment_success_signal_creates_single_notification(self):
        booking = self.create_booking(public_number='BK-PAY-001')
        payment = self.create_payment(booking=booking, status='pending')

        payment.status = 'succeeded'
        payment.paid_at = timezone.now()
        payment.save()
        payment.save()

        self.assertEqual(Notification.objects.filter(type='payment_success').count(), 1)
        self.assertEqual(NotificationLog.objects.filter(event_type='payment_success').count(), 1)

        notification = Notification.objects.get(type='payment_success')
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.data_json['payment_id'], payment.id)

    def test_register_device_updates_existing_token(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            'fcm_token': 'token123',
            'platform': 'android',
            'device_id': 'device123',
            'app_version': '1.0.0',
        }

        response = self.client.post('/api/v1/notifications/register-device/', payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserDevice.objects.count(), 1)

        payload['app_version'] = '1.1.0'
        response = self.client.post('/api/v1/notifications/register-device/', payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserDevice.objects.count(), 1)
        self.assertEqual(UserDevice.objects.get(fcm_token='token123').app_version, '1.1.0')

    def test_admin_can_send_notification_using_message_alias(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            'target': 'user',
            'user_id': self.user.id,
            'title': 'Broadcast',
            'message': 'Hello from admin',
            'data': {'source': 'admin'},
        }

        response = self.client.post('/api/v1/admin/notifications/send/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get(type='admin_broadcast')
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.body, 'Hello from admin')
        self.assertEqual(notification.data_json, {'source': 'admin'})
