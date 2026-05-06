from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType
from payments.models import Payment

class UserAuthTests(APITestCase):
    def test_register_user(self):
        url = reverse('auth_register')
        data = {
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'full_name': 'Test User',
            'phone': '+1234567890'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().email, 'testuser@example.com')

    def test_login_user(self):
        # First register
        user = User.objects.create_user(
            username='testlogin@example.com',
            email='testlogin@example.com',
            password='testpassword123'
        )
        url = reverse('token_obtain_pair')
        data = {
            'email': 'testlogin@example.com',
            'password': 'testpassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_get_profile(self):
        user = User.objects.create_user(
            username='profile@example.com',
            email='profile@example.com',
            password='testpassword123',
            full_name='Profile User'
        )
        from users.models import UserProfile
        UserProfile.objects.get_or_create(user=user)
        
        self.client.force_authenticate(user=user)
        url = reverse('profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'Profile User')

    def test_get_profile_includes_user_bookings(self):
        user = User.objects.create_user(
            username='bookings-profile@example.com',
            email='bookings-profile@example.com',
            password='testpassword123',
            full_name='Bookings User'
        )
        other_user = User.objects.create_user(
            username='other-profile@example.com',
            email='other-profile@example.com',
            password='testpassword123'
        )
        from users.models import UserProfile
        UserProfile.objects.get_or_create(user=user)

        vehicle_type = VehicleType.objects.create(code='scooter', name='Scooter')
        vehicle_model = VehicleModel.objects.create(
            name='NMAX',
            brand='Yamaha',
            type=vehicle_type,
            engine_cc=155,
            transmission='auto',
            fuel_consumption=2.5,
            year=2024,
            trunk='large',
            helmets_count=2,
            description='test',
            rental_terms='test',
        )
        vehicle = Vehicle.objects.create(
            model=vehicle_model,
            title='Yamaha NMAX',
            slug='yamaha-nmax',
            sku='NMAX-001',
            color='black',
            base_price_usd=Decimal('20.00'),
            status='available',
        )

        user_booking = Booking.objects.create(
            public_number='BK-PROFILE-1',
            user=user,
            vehicle=vehicle,
            start_at=timezone.now() + timedelta(days=2),
            end_at=timezone.now() + timedelta(days=4),
            subtotal_usd=Decimal('40.00'),
            addons_total_usd=Decimal('0.00'),
            discount_usd=Decimal('0.00'),
            markup_usd=Decimal('0.00'),
            delivery_price_usd=Decimal('0.00'),
            total_usd=Decimal('40.00'),
            total_display='$40.00',
            payment_method='online_card',
            currency='USD',
            status='confirmed',
            payment_status='pending',
        )
        Booking.objects.create(
            public_number='BK-PROFILE-OTHER',
            user=other_user,
            vehicle=vehicle,
            start_at=timezone.now() + timedelta(days=5),
            end_at=timezone.now() + timedelta(days=6),
            subtotal_usd=Decimal('20.00'),
            addons_total_usd=Decimal('0.00'),
            discount_usd=Decimal('0.00'),
            markup_usd=Decimal('0.00'),
            delivery_price_usd=Decimal('0.00'),
            total_usd=Decimal('20.00'),
            total_display='$20.00',
            payment_method='online_card',
            currency='USD',
            status='created',
            payment_status='pending',
        )
        Payment.objects.create(
            booking=user_booking,
            provider='stripe',
            method='card',
            amount_usd=Decimal('40.00'),
            amount_display='$40.00',
            currency='USD',
            status='pending',
        )

        self.client.force_authenticate(user=user)
        url = reverse('profile')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bookings', response.data)
        self.assertEqual(len(response.data['bookings']), 1)
        self.assertEqual(response.data['bookings'][0]['order_number'], 'BK-PROFILE-1')
        self.assertEqual(response.data['bookings'][0]['latest_payment']['provider'], 'stripe')

    def test_update_profile(self):
        user = User.objects.create_user(
            username='update@example.com',
            email='update@example.com',
            password='testpassword123'
        )
        from users.models import UserProfile
        UserProfile.objects.get_or_create(user=user)

        self.client.force_authenticate(user=user)
        url = reverse('profile')
        data = {
            'full_name': 'Updated Name',
            'phone': '+999999999',
            'country': 'Indonesia'
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.full_name, 'Updated Name')
        self.assertEqual(user.profile.country, 'Indonesia')
