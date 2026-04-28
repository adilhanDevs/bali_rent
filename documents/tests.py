from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import UserDocument
import io
from PIL import Image

User = get_user_model()

def create_test_image():
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), 'white')
    image.save(file, 'PNG')
    file.name = 'test.png'
    file.seek(0)
    return file

class DocumentAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='password', username='user')
        self.other_user = User.objects.create_user(email='other@example.com', password='password', username='other')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='password', username='admin', role='admin')
        
    def test_upload_document(self):
        self.client.force_authenticate(user=self.user)
        image = create_test_image()
        data = {
            'document_type': 'passport',
            'file': SimpleUploadedFile('test.png', image.read(), content_type='image/png')
        }
        response = self.client.post('/api/v1/documents/', data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(UserDocument.objects.count(), 1)

    def test_view_own_documents(self):
        UserDocument.objects.create(user=self.user, document_type='passport', status='pending')
        UserDocument.objects.create(user=self.other_user, document_type='passport', status='pending')
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/documents/')
        self.assertEqual(len(response.data['results']), 1)

    def test_cannot_view_others_documents(self):
        doc = UserDocument.objects.create(user=self.other_user, document_type='passport', status='pending')
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/documents/{doc.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_approve_document(self):
        doc = UserDocument.objects.create(user=self.user, document_type='passport', status='pending')
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/v1/admin/documents/{doc.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'approved')
        self.assertEqual(doc.reviewed_by, self.admin)

    def test_admin_reject_document(self):
        doc = UserDocument.objects.create(user=self.user, document_type='passport', status='pending')
        
        self.client.force_authenticate(user=self.admin)
        data = {'rejection_reason': 'Blurry image'}
        response = self.client.post(f'/api/v1/admin/documents/{doc.id}/reject/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'rejected')
        self.assertEqual(doc.rejection_reason, 'Blurry image')

    def test_file_type_validation(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'document_type': 'passport',
            'file': SimpleUploadedFile('test.txt', b'text content', content_type='text/plain')
        }
        response = self.client.post('/api/v1/documents/', data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)
