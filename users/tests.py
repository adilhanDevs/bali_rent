from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User

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
