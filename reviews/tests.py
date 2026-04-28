from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from catalog.models import Vehicle, VehicleType, VehicleModel
from bookings.models import Booking
from reviews.models import Review
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

class ReviewAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='password', username='user')
        self.other_user = User.objects.create_user(email='other@example.com', password='password', username='other')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='password', username='admin', role='admin')
        
        self.vt = VehicleType.objects.create(code='scooter', name='Scooter')
        self.vm = VehicleModel.objects.create(
            name='NMAX', brand='Yamaha', type=self.vt, engine_cc=155, 
            transmission='auto', fuel_consumption=2.5, year=2023, 
            trunk='large', helmets_count=2, description='test', rental_terms='test'
        )
        self.scooter = Vehicle.objects.create(
            model=self.vm, title='Yamaha NMAX 2023', slug='nmax-2023', 
            sku='NMAX001', color='black', base_price_usd=Decimal('20.00'), status='available'
        )
        
        self.booking = Booking.objects.create(
            public_number='BK-123', user=self.user, vehicle=self.scooter,
            start_at=timezone.now(), end_at=timezone.now(),
            subtotal_usd=20, total_usd=20, status='completed'
        )

    def test_create_review_success(self):
        self.client.force_authenticate(user=self.user)
        url = f'/api/v1/scooters/{self.scooter.id}/reviews/'
        data = {
            'scooter': self.scooter.id,
            'booking': self.booking.id,
            'rating': 5,
            'comment': 'Great scooter!'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.first().status, 'pending')

    def test_create_review_not_own_booking(self):
        self.client.force_authenticate(user=self.other_user)
        url = f'/api/v1/scooters/{self.scooter.id}/reviews/'
        data = {
            'scooter': self.scooter.id,
            'booking': self.booking.id,
            'rating': 5,
            'comment': 'Fake review'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_review_booking_not_completed(self):
        self.booking.status = 'active'
        self.booking.save()
        
        self.client.force_authenticate(user=self.user)
        url = f'/api/v1/scooters/{self.scooter.id}/reviews/'
        data = {
            'scooter': self.scooter.id,
            'booking': self.booking.id,
            'rating': 5,
            'comment': 'Still riding'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_approve_and_stats_update(self):
        review = Review.objects.create(
            user=self.user, scooter=self.scooter, booking=self.booking,
            rating=5, comment='Amazing', status='pending'
        )
        
        self.client.force_authenticate(user=self.admin)
        url = f'/api/v1/admin/reviews/{review.id}/approve/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.scooter.refresh_from_db()
        self.assertEqual(self.scooter.rating_avg, 5.0)
        self.assertEqual(self.scooter.reviews_count, 1)

    def test_one_review_per_booking(self):
        Review.objects.create(
            user=self.user, scooter=self.scooter, booking=self.booking,
            rating=5, comment='Amazing', status='approved'
        )
        
        self.client.force_authenticate(user=self.user)
        url = f'/api/v1/scooters/{self.scooter.id}/reviews/'
        data = {
            'scooter': self.scooter.id,
            'booking': self.booking.id,
            'rating': 4,
            'comment': 'Another review'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
