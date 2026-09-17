import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User
from sitecontent.models import SiteContentEntry
from sitecontent.services import build_public_dictionary_overrides


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class SiteContentHeroVideoTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_sitecontent',
            email='admin@test.com',
            password='adminpassword123',
            role='admin',
            is_staff=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_create_and_delete_video_with_file_cleanup(self):
        fake_video_bytes = b'fake_mp4_video_content_data'
        video_file = SimpleUploadedFile(
            'hero_test.mp4', fake_video_bytes, content_type='video/mp4'
        )

        entry = SiteContentEntry.objects.create(
            key='media.home.heroVideo',
            language='all',
            value_type='video',
            media=video_file,
            is_active=True,
        )

        self.assertTrue(entry.media.storage.exists(entry.media.name))

        overrides = build_public_dictionary_overrides('en')
        self.assertIn('media', overrides)
        self.assertIn('home', overrides['media'])
        self.assertIn('heroVideo', overrides['media']['home'])
        self.assertTrue(overrides['media']['home']['heroVideo'].endswith('.mp4'))

        file_name = entry.media.name
        entry.delete()

        # Check that post_delete signal cleaned up the file
        self.assertFalse(entry.media.storage.exists(file_name))

    def test_overrides_return_empty_string_for_none(self):
        entry = SiteContentEntry.objects.create(
            key='media.home.heroVideo',
            language='all',
            value_type='video',
            value='__none__',
            is_active=True,
        )
        overrides = build_public_dictionary_overrides('en')
        self.assertEqual(overrides['media']['home']['heroVideo'], '')
        entry.delete()

    def test_admin_api_upload_and_delete_hero_video(self):
        fake_video = SimpleUploadedFile(
            'uploaded_hero.mp4', b'dummy_video_bytes', content_type='video/mp4'
        )
        url = reverse('admin-site-content-list')

        # 1. Create via API
        response = self.client.post(
            url,
            {
                'key': 'media.home.heroVideo',
                'language': 'all',
                'value_type': 'video',
                'media': fake_video,
                'is_active': True,
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry_id = response.data['id']
        entry = SiteContentEntry.objects.get(id=entry_id)
        self.assertTrue(entry.media)
        file_name = entry.media.name

        # 2. Delete via API
        del_url = reverse('admin-site-content-detail', args=[entry_id])
        del_response = self.client.delete(del_url)
        self.assertEqual(del_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(entry.media.storage.exists(file_name))

    def test_admin_api_replace_hero_video_cleans_old_file(self):
        video1 = SimpleUploadedFile('vid1.mp4', b'video_1', content_type='video/mp4')
        video2 = SimpleUploadedFile('vid2.mp4', b'video_2', content_type='video/mp4')
        url = reverse('admin-site-content-list')

        res1 = self.client.post(
            url,
            {
                'key': 'media.home.heroVideo',
                'language': 'all',
                'value_type': 'video',
                'media': video1,
                'is_active': True,
            },
            format='multipart',
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        entry_id = res1.data['id']
        entry1 = SiteContentEntry.objects.get(id=entry_id)
        old_file_name = entry1.media.name
        self.assertTrue(entry1.media.storage.exists(old_file_name))

        # Update with new video
        detail_url = reverse('admin-site-content-detail', args=[entry_id])
        res2 = self.client.patch(
            detail_url,
            {
                'media': video2,
            },
            format='multipart',
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        entry2 = SiteContentEntry.objects.get(id=entry_id)
        new_file_name = entry2.media.name
        self.assertNotEqual(old_file_name, new_file_name)
        self.assertFalse(entry2.media.storage.exists(old_file_name))
        self.assertTrue(entry2.media.storage.exists(new_file_name))

        # Cleanup
        entry2.delete()
        self.assertFalse(entry2.media.storage.exists(new_file_name))
