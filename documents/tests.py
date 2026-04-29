from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import DocumentVerification, UserDocument

User = get_user_model()


def upload_test_file(name='test.gif'):
    return SimpleUploadedFile(
        name,
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
        b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00'
        b'\x00\x02\x02D\x01\x00;',
        content_type='image/gif' if name.endswith('.gif') else 'image/png',
    )


class DocumentAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='password', username='user')
        self.other_user = User.objects.create_user(email='other@example.com', password='password', username='other')
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password',
            username='admin',
            role='admin',
        )
        self.manager = User.objects.create_user(
            email='manager@example.com',
            password='password',
            username='manager',
            role='manager',
        )

    def test_upload_document(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/v1/documents/',
            {
                'document_type': 'passport',
                'file': upload_test_file('passport.png'),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
        document = UserDocument.objects.get()
        self.assertTrue(document.file.name.startswith(f'user_documents/user_{self.user.id}/'))

    def test_view_own_documents_only(self):
        UserDocument.objects.create(user=self.user, document_type='passport', status='pending', file=upload_test_file('a.png'))
        UserDocument.objects.create(user=self.other_user, document_type='passport', status='pending', file=upload_test_file('b.png'))

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/documents/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_view_my_documents_endpoint(self):
        own_document = UserDocument.objects.create(
            user=self.user,
            document_type='passport',
            status='approved',
            file=upload_test_file('mine.png'),
        )
        UserDocument.objects.create(
            user=self.other_user,
            document_type='driver_license',
            status='rejected',
            file=upload_test_file('other.png'),
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/documents/my/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], own_document.id)
        self.assertEqual(response.data['results'][0]['status'], 'approved')

    def test_upload_document_supports_type_alias(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/v1/documents/',
            {
                'type': 'passport',
                'file': upload_test_file('passport-alias.png'),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['document_type'], 'passport')
        self.assertEqual(response.data['status'], 'pending')

    def test_cannot_view_others_documents(self):
        document = UserDocument.objects.create(
            user=self.other_user,
            document_type='passport',
            status='pending',
            file=upload_test_file('other.png'),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/documents/{document.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_approve_document_creates_verification(self):
        document = UserDocument.objects.create(
            user=self.user,
            document_type='passport',
            status='pending',
            file=upload_test_file('pending.png'),
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/v1/admin/documents/{document.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.status, 'approved')
        self.assertEqual(document.reviewed_by, self.admin)
        verification = document.verifications.get()
        self.assertEqual(verification.status, 'approved')
        self.assertEqual(verification.verified_by, self.admin)

    def test_manager_reject_document_creates_verification(self):
        document = UserDocument.objects.create(
            user=self.user,
            document_type='passport',
            status='pending',
            file=upload_test_file('reject.png'),
        )
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            f'/api/v1/admin/documents/{document.id}/reject/',
            {'rejection_reason': 'Blurry image'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.status, 'rejected')
        self.assertEqual(document.rejection_reason, 'Blurry image')
        verification = document.verifications.get()
        self.assertEqual(verification.status, 'rejected')
        self.assertEqual(verification.verified_by, self.manager)

    def test_file_type_validation(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/v1/documents/',
            {
                'document_type': 'passport',
                'file': SimpleUploadedFile('test.txt', b'text', content_type='text/plain'),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    def test_file_mime_type_validation(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/v1/documents/',
            {
                'document_type': 'passport',
                'file': SimpleUploadedFile('passport.png', b'not really png', content_type='text/plain'),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    def test_admin_access_is_forbidden_for_regular_user(self):
        document = UserDocument.objects.create(
            user=self.user,
            document_type='passport',
            status='pending',
            file=upload_test_file('forbidden.png'),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/admin/documents/{document.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
