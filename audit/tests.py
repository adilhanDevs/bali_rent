from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from users.models import User
from .models import AuditLog, AdminLoginLog
from pricing.models import Season
from django.contrib.auth.signals import user_logged_in

class AuditAPITest(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(email='admin@example.com', username='admin', password='password')
        self.client_user = User.objects.create_user(email='client@example.com', username='client', password='password')
        self.season_url = reverse('admin-season-list')

    def test_admin_only_access(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(reverse('admin-audit-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_mutation_logged(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {"name": "Summer 2026", "start_date": "2026-06-01", "end_date": "2026-08-31"}
        response = self.client.post(self.season_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.assertEqual(AuditLog.objects.count(), 1)
        log = AuditLog.objects.first()
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.after_json['name'], "Summer 2026")
        self.assertEqual(log.user, self.admin_user)

    def test_update_mutation_logged_with_snapshot(self):
        season = Season.objects.create(name="Old Name", start_date="2026-01-01", end_date="2026-02-01")
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-season-detail', kwargs={'pk': season.pk})
        
        response = self.client.patch(url, {"name": "New Name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        log = AuditLog.objects.filter(action='update').first()
        self.assertEqual(log.before_json['name'], "Old Name")
        self.assertEqual(log.after_json['name'], "New Name")

    def test_delete_mutation_logged(self):
        season = Season.objects.create(name="Delete Me", start_date="2026-01-01", end_date="2026-02-01")
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-season-detail', kwargs={'pk': season.pk})
        
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        log = AuditLog.objects.filter(action='delete').first()
        self.assertEqual(log.before_json['name'], "Delete Me")

    def test_admin_login_logged(self):
        # Trigger the signal manually for testing if needed, 
        # or use client.login (but client.login doesn't always trigger DRF signals same way)
        user_logged_in.send(sender=User, request=self.client.request().wsgi_request, user=self.admin_user)
        self.assertTrue(AdminLoginLog.objects.filter(user=self.admin_user).exists())
