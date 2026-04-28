from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from users.models import User
from .models import AnalyticsEvent

class AnalyticsAPITest(APITestCase):
    def setUp(self):
        self.url = reverse('analytics-events')
        self.user = User.objects.create_user(email='test@example.com', username='test', password='password')

    def test_anonymous_event_saved(self):
        payload = {"screen": "home", "action": "view"}
        response = self.client.post(self.url, {"event_name": "page_view", "payload": payload}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        self.assertEqual(event.event_name, "page_view")
        self.assertIsNone(event.user)

    def test_authenticated_event_saved(self):
        self.client.force_authenticate(user=self.user)
        payload = {"booking_id": 123}
        response = self.client.post(self.url, {"event_name": "start_checkout", "payload": payload}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = AnalyticsEvent.objects.first()
        self.assertEqual(event.user, self.user)

    def test_very_large_payload_rejected(self):
        # Create a payload > 10KB
        large_payload = {"data": "x" * 11000}
        response = self.client.post(self.url, {"event_name": "large_event", "payload": large_payload}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Payload too large", str(response.data['payload']))
