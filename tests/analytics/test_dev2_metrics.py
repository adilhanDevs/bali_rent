import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from support.models import SupportTicket
from chat.models import ChatMessage, ChatThread
from reviews.models import Review
from analytics.dev2_metrics import get_tickets_count, get_messages_count, get_reviews_count, get_active_users
from analytics.views_dev2 import Dev2AnalyticsViewSet

User = get_user_model()

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email='admin@example.com', username='admin', password='password', role='admin')

@pytest.fixture
def manager_user(db):
    return User.objects.create_user(email='manager@example.com', username='manager', password='password', role='manager')

@pytest.fixture
def staff_user(db):
    return User.objects.create_user(email='staff@example.com', username='staff', password='password', role='staff')

@pytest.fixture
def client_user(db):
    return User.objects.create_user(email='client@example.com', username='client', password='password', role='client')

@pytest.mark.django_db
def test_dev2_metrics_logic(admin_user):
    # Clear existing if any
    SupportTicket.objects.all().delete()
    ChatMessage.objects.all().delete()
    Review.objects.all().delete()

    SupportTicket.objects.create(user=admin_user, subject="T1", channel="app")
    
    thread = ChatThread.objects.create(title="Thread 1")
    from chat.models import ChatParticipant
    ChatParticipant.objects.create(thread=thread, user=admin_user, role=ChatParticipant.ROLE_STAFF)
    ChatMessage.objects.create(thread=thread, sender=admin_user, text="Msg 1")
    
    from catalog.models import Vehicle, VehicleModel, VehicleType
    vt, _ = VehicleType.objects.get_or_create(code="scooter", name="Scooter")
    vm, _ = VehicleModel.objects.get_or_create(
        name="M1", 
        brand="B1", 
        type=vt,
        defaults={
            "engine_cc": 150,
            "transmission": "auto",
            "fuel_consumption": 2.5,
            "year": 2024,
            "trunk": "medium",
            "description": "desc",
            "rental_terms": "terms"
        }
    )
    v, _ = Vehicle.objects.get_or_create(
        model=vm, 
        title="V1", 
        sku="S1", 
        defaults={
            "base_price_usd": 10,
            "slug": "v1-slug",
            "color": "black"
        }
    )
    Review.objects.create(scooter=v, user=admin_user, rating=5)

    assert get_tickets_count() == 1
    assert get_messages_count() == 1
    assert get_reviews_count() == 1
    
    # Active users (admin_user logged in at creation usually, or we can force it)
    admin_user.last_login = timezone_now()
    admin_user.save()
    assert get_active_users() >= 1

@pytest.mark.django_db
def test_dev2_analytics_viewset_direct(admin_user, manager_user, client_user):
    from rest_framework.test import APIRequestFactory
    from rest_framework.test import force_authenticate
    
    factory = APIRequestFactory()
    view = Dev2AnalyticsViewSet.as_view({'get': 'list'})

    # Admin - OK
    request = factory.get('/api/v1/admin/analytics/dev2/')
    force_authenticate(request, user=admin_user)
    response = view(request)
    assert response.status_code == status.HTTP_200_OK
    assert "tickets" in response.data

    # Manager - OK
    request = factory.get('/api/v1/admin/analytics/dev2/')
    force_authenticate(request, user=manager_user)
    response = view(request)
    assert response.status_code == status.HTTP_200_OK

    # Client - Forbidden
    request = factory.get('/api/v1/admin/analytics/dev2/')
    force_authenticate(request, user=client_user)
    response = view(request)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def timezone_now():
    from django.utils import timezone
    return timezone.now()
