from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from support.models import SupportTicket
from chat.models import ChatMessage
from reviews.models import Review

User = get_user_model()

def get_tickets_count():
    return SupportTicket.objects.count()

def get_messages_count():
    return ChatMessage.objects.count()

def get_reviews_count():
    return Review.objects.count()

def get_active_users(days=30):
    since = timezone.now() - timedelta(days=days)
    return User.objects.filter(last_login__gte=since).count()
