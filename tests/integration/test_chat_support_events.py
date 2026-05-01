import pytest
from django.core.cache import cache
from events.services import emit_event
from chat.models import ChatThread, ChatMessage, ChatParticipant
from support.models import SupportTicket
from support.services import SupportTicketService

pytestmark = pytest.mark.django_db

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()

def test_support_ticket_service_automatically_creates_chat_thread(user):
    # This tests the integration through the service
    ticket = SupportTicketService.create_ticket(
        user=user,
        subject="Automatic thread test",
        channel="app"
    )
    
    # Check if thread was created automatically via event emitted in service
    thread = ChatThread.objects.get(title=f"Support Ticket #{ticket.id}")
    assert thread.created_by == user
    assert ChatParticipant.objects.filter(thread=thread, user=user).exists()

def test_support_ticket_service_automatically_syncs_message(user):
    ticket = SupportTicketService.create_ticket(
        user=user,
        subject="Message sync test",
        channel="app"
    )
    
    SupportTicketService.create_message(
        ticket=ticket,
        sender=user,
        message="Test message from service"
    )
    
    thread = ChatThread.objects.get(title=f"Support Ticket #{ticket.id}")
    assert ChatMessage.objects.filter(thread=thread, text="Test message from service").exists()

def test_ticket_created_creates_thread(user):
    ticket_id = 123
    emit_event(
        "ticket_created",
        {
            "user": user,
            "ticket_id": ticket_id,
        },
    )
    
    thread = ChatThread.objects.get(title=f"Support Ticket #{ticket_id}")
    assert thread.created_by == user
    assert thread.status == ChatThread.STATUS_OPEN
    assert ChatParticipant.objects.filter(thread=thread, user=user).exists()

def test_message_sent_creates_message_in_chat(user):
    ticket_id = 124
    # Create thread first
    emit_event(
        "ticket_created",
        {
            "user": user,
            "ticket_id": ticket_id,
        },
    )
    thread = ChatThread.objects.get(title=f"Support Ticket #{ticket_id}")
    
    # Send message event
    emit_event(
        "message_sent",
        {
            "user": user,
            "ticket_id": ticket_id,
            "message_id": 500,
            "text": "Hello support",
        },
    )
    
    message = ChatMessage.objects.get(thread=thread, text="Hello support")
    assert message.sender == user

def test_duplicate_event_no_duplicate_thread(user):
    ticket_id = 125
    payload = {
        "user": user,
        "ticket_id": ticket_id,
    }
    
    emit_event("ticket_created", payload)
    emit_event("ticket_created", payload)
    
    assert ChatThread.objects.filter(title=f"Support Ticket #{ticket_id}").count() == 1

def test_duplicate_message_event_no_duplicate_message(user):
    ticket_id = 125
    emit_event("ticket_created", {"user": user, "ticket_id": ticket_id})
    
    payload = {
        "user": user,
        "ticket_id": ticket_id,
        "message_id": 600,
        "text": "Duplicate test",
    }
    
    emit_event("message_sent", payload)
    emit_event("message_sent", payload)
    
    thread = ChatThread.objects.get(title=f"Support Ticket #{ticket_id}")
    assert ChatMessage.objects.filter(thread=thread, text="Duplicate test").count() == 1

def test_fallback_works(user):
    # message_sent event without previous ticket_created event
    ticket_id = 126
    
    # Create the ticket in DB for fallback to work
    ticket = SupportTicket.objects.create(
        id=ticket_id,
        user=user,
        subject="Test Ticket",
        channel="app"
    )
    
    emit_event(
        "message_sent",
        {
            "user": user,
            "ticket_id": ticket_id,
            "message_id": 501,
            "text": "Fallback message",
        },
    )
    
    thread = ChatThread.objects.get(title=f"Support Ticket #{ticket_id}")
    assert ChatMessage.objects.filter(thread=thread, text="Fallback message").exists()

def test_support_staff_message_syncs_to_chat(user, admin_user):
    ticket_id = 127
    emit_event(
        "ticket_created",
        {
            "user": user,
            "ticket_id": ticket_id,
        },
    )
    
    # Staff sends message
    emit_event(
        "message_sent",
        {
            "user": admin_user,
            "ticket_id": ticket_id,
            "message_id": 502,
            "text": "How can I help you?",
        },
    )
    
    thread = ChatThread.objects.get(title=f"Support Ticket #{ticket_id}")
    message = ChatMessage.objects.get(thread=thread, sender=admin_user)
    assert message.text == "How can I help you?"
    
    # Check participant role
    participant = ChatParticipant.objects.get(thread=thread, user=admin_user)
    assert participant.role == ChatParticipant.ROLE_STAFF
