from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User
from .models import Addon

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
            'price': '5.00',
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
            'price': '-5.00',
            'price_type': 'per_day'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('price', response.data)

    def test_client_cannot_create_addon(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('addon-list')
        data = {'name': 'New'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
