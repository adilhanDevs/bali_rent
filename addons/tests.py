from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User
from catalog.models import Vehicle, VehicleModel, VehicleType
from bookings.models import Booking, BookingAddon
from .models import Addon
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from bookings.serializers import BookingSerializer

class AddonTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin@example.com',
            email='admin@example.com',
            password='adminpassword',
            role='admin'
        )
        self.client_user = User.objects.create_user(
            username='client@example.com',
            email='client@example.com',
            password='clientpassword'
        )
        self.addon_active = Addon.objects.create(
            code='helmet', name='Helmet', description='Extra helmet',
            price_usd=2.00, price_type='per_day', is_active=True
        )
        self.addon_inactive = Addon.objects.create(
            code='gopro', name='GoPro', description='Action camera',
            price_usd=10.00, price_type='per_day', is_active=False
        )

    def test_public_list_addons(self):
        url = reverse('addon-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Results is paginated
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['code'], 'helmet')

    def test_admin_list_all_addons(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('addon-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_admin_create_addon(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('addon-list')
        data = {
            'code': 'wifi',
            'name': 'Pocket WiFi',
            'description': '4G WiFi',
            'price_usd': '5.00',
            'price_type': 'per_day',
            'is_active': True
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Addon.objects.count(), 3)

    def test_admin_create_addon_negative_price(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('addon-list')
        data = {
            'code': 'bad',
            'name': 'Bad Addon',
            'description': 'Negative price',
            'price_usd': '-5.00',
            'price_type': 'per_day'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('price_usd', response.data)

    def test_client_cannot_create_addon(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('addon-list')
        data = {'name': 'New'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_addon_in_use_and_keep_booking_snapshots(self):
        self.client.force_authenticate(user=self.admin_user)
        vehicle_type = VehicleType.objects.create(code='scooter', name='Scooter')
        vehicle_model = VehicleModel.objects.create(
            name='NMAX',
            brand='Yamaha',
            type=vehicle_type,
            engine_cc=155,
            transmission='auto',
            fuel_consumption=Decimal('2.50'),
            year=2024,
            trunk='large',
            helmets_count=2,
            description='test',
            rental_terms='test',
        )
        vehicle = Vehicle.objects.create(
            model=vehicle_model,
            title='Yamaha NMAX',
            slug='yamaha-nmax-test',
            sku='NMAX-TEST',
            color='black',
            base_price_usd=Decimal('25.00'),
            status='available',
        )
        booking = Booking.objects.create(
            public_number='BK-ADDON',
            user=self.client_user,
            vehicle=vehicle,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=3),
            payment_method='online_card',
            currency='USD',
            subtotal_usd=Decimal('50.00'),
            addons_total_usd=Decimal('2.00'),
            delivery_price_usd=Decimal('0.00'),
            discount_usd=Decimal('0.00'),
            markup_usd=Decimal('0.00'),
            total_usd=Decimal('52.00'),
            total_display='USD 52.00',
            status='created',
        )
        booking_addon = BookingAddon.objects.create(
            booking=booking,
            addon=self.addon_active,
            name_snapshot=self.addon_active.name,
            price_usd_snapshot=self.addon_active.price_usd,
            quantity=1,
        )
        url = reverse('addon-detail', args=[self.addon_active.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Addon.objects.filter(id=self.addon_active.id).exists())

        booking_addon.refresh_from_db()
        self.assertIsNone(booking_addon.addon)
        self.assertEqual(booking_addon.name_snapshot, 'Helmet')
        self.assertEqual(booking_addon.price_usd_snapshot, Decimal('2.00'))

        serialized_booking = BookingSerializer(booking).data
        self.assertEqual(serialized_booking['add_ons'][0]['id'], None)
        self.assertEqual(serialized_booking['add_ons'][0]['name'], 'Helmet')
        self.assertEqual(serialized_booking['add_ons'][0]['price'], '2.00')
