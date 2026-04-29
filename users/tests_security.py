from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User, UserProfile
from audit.models import AuditLog
import json

class UserSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('auth_register')
        self.login_url = reverse('token_obtain_pair')
        self.refresh_url = reverse('token_refresh')
        self.logout_url = reverse('auth_logout')
        self.profile_url = reverse('profile')
        self.user_me_url = reverse('user-me')
        
        self.user_data = {
            'email': 'test@example.com',
            'password': 'StrongPassword123!',
            'full_name': 'Test User',
            'phone': '+1234567890'
        }
        
        # Create an admin user
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            username='admin@example.com',
            password='AdminPassword123!',
            role='admin'
        )
        
    def test_registration_and_duplicate_handling(self):
        # Successful registration
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.user_data['email']).exists())
        
        # Duplicate email
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        
        # Duplicate phone (should be rejected)
        new_user_data = self.user_data.copy()
        new_user_data['email'] = 'test2@example.com'
        response = self.client.post(self.register_url, new_user_data)
        # We expect this to fail currently, so this test will fail until we fix it.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, "Duplicate phone should be rejected")

    def test_login_and_token_refresh(self):
        User.objects.create_user(
            email=self.user_data['email'],
            username=self.user_data['email'],
            password=self.user_data['password']
        )
        
        # Valid login
        response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        refresh_token = response.data['refresh']
        
        # Invalid login
        response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)
        
        # Token refresh
        response = self.client.post(self.refresh_url, {'refresh': refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_logout(self):
        user = User.objects.create_user(
            email=self.user_data['email'],
            username=self.user_data['email'],
            password=self.user_data['password']
        )
        login_resp = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        refresh_token = login_resp.data['refresh']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
        
        response = self.client.post(self.logout_url, {'refresh': refresh_token})
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT, "Logout should return 205")

    def test_profile_security_and_role_escalation(self):
        user = User.objects.create_user(
            email=self.user_data['email'],
            username=self.user_data['email'],
            password=self.user_data['password'],
            role='client'
        )
        UserProfile.objects.create(user=user)
        
        login_resp = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
        
        # Access own profile
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user_data['email'])
        self.assertNotIn('password', response.data)
        
        # Try to escalate role via /me/ (UserViewSet action)
        response = self.client.patch(self.user_me_url, {'role': 'admin', 'is_active': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.role, 'client') # Should NOT change
        self.assertTrue(user.is_active) # Should NOT change
        
        # Try to modify fields not in serializer (e.g. is_staff)
        response = self.client.patch(self.user_me_url, {'is_staff': True})
        user.refresh_from_db()
        self.assertFalse(user.is_staff)

    def test_admin_access_control(self):
        user = User.objects.create_user(
            email=self.user_data['email'],
            username=self.user_data['email'],
            password=self.user_data['password'],
            role='client'
        )
        login_resp = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        
        # Normal user tries to list users
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin tries to list users
        admin_login_resp = self.client.post(self.login_url, {
            'email': 'admin@example.com',
            'password': 'AdminPassword123!'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_login_resp.data['access']}")
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_admin_mutation_audit_log(self):
        # Admin updates a user
        user_to_update = User.objects.create_user(
            email='to_update@example.com',
            username='to_update@example.com',
            password='Password123!'
        )
        
        admin_login_resp = self.client.post(self.login_url, {
            'email': 'admin@example.com',
            'password': 'AdminPassword123!'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_login_resp.data['access']}")
        
        # Use AdminUserViewSet endpoint
        url = reverse('admin-user-detail', kwargs={'pk': user_to_update.id})
        response = self.client.patch(url, {'full_name': 'Updated Name', 'role': 'manager'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        user_to_update.refresh_from_db()
        self.assertEqual(user_to_update.full_name, 'Updated Name')
        self.assertEqual(user_to_update.role, 'manager')
        
        # Check if AuditLog was created
        self.assertTrue(AuditLog.objects.filter(action='update', object_id=str(user_to_update.id)).exists(), "Audit log should be created for admin mutation")
