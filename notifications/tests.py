from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Notification
from users.models import UserDevice
import json

User = get_user_model()

class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='password', username='user')
        self.other_user = User.objects.create_user(email='other@example.com', password='password', username='other')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='password', username='admin', role='admin')
        
        self.notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            body='Test message',
            type='test',
            data_json={'key': 'value'}
        )

    def test_list_notifications(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test Notification')
        self.assertEqual(response.data['results'][0]['message'], 'Test message')

    def test_user_sees_only_own_notifications(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(len(response.data['results']), 0)

    def test_mark_read(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/notifications/{self.notification.id}/mark-read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_mark_all_read(self):
        Notification.objects.create(user=self.user, title='N2', body='B2', type='t')
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/notifications/mark-all-read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

    def test_register_device(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'fcm_token': 'token123',
            'platform': 'android',
            'device_id': 'id123',
            'app_version': '1.0'
        }
        response = self.client.post('/api/v1/notifications/register-device/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserDevice.objects.count(), 1)
        
        # Update existing token
        data['app_version'] = '1.1'
        response = self.client.post('/api/v1/notifications/register-device/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(UserDevice.objects.count(), 1)
        self.assertEqual(UserDevice.objects.get(fcm_token='token123').app_version, '1.1')

    def test_admin_send_specific_user(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'target': 'user',
            'user_id': self.user.id,
            'title': 'Admin Title',
            'message': 'Admin message'
        }
        response = self.client.post('/api/v1/admin/notifications/send/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(user=self.user, title='Admin Title').count(), 1)

    def test_admin_send_all_users(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'target': 'all',
            'title': 'Broadcast',
            'message': 'Hello everyone'
        }
        response = self.client.post('/api/v1/admin/notifications/send/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 3 users: user, other_user, admin
        self.assertEqual(Notification.objects.filter(title='Broadcast').count(), 3)
