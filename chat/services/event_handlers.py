import logging
from django.core.cache import cache
from django.db import transaction
from django.contrib.auth import get_user_model

from chat.models import ChatThread, ChatMessage, ChatParticipant

logger = logging.getLogger(__name__)
User = get_user_model()

def handle_ticket_created(payload):
    """
    Handles 'ticket_created' event:
    - gets user from payload
    - creates ChatThread if not exists: user = user, status = "open"
    - stores mapping: ticket_id -> thread_id (using cache)
    """
    try:
        user = payload.get('user')
        ticket_id = payload.get('ticket_id')
        
        if not user or not ticket_id:
            logger.warning(f"handle_ticket_created: Missing user or ticket_id in payload: {payload}")
            return None
            
        mapping_key = f"support_ticket_thread_map:{ticket_id}"
        thread_id = cache.get(mapping_key)
        
        if thread_id:
            thread = ChatThread.objects.filter(id=thread_id).first()
            if thread:
                return thread
        
        with transaction.atomic():
            # Create thread
            thread = ChatThread.objects.create(
                title=f"Support Ticket #{ticket_id}",
                status=ChatThread.STATUS_OPEN,
                created_by=user
            )
            # Add user as participant
            ChatParticipant.objects.get_or_create(
                thread=thread,
                user=user,
                defaults={'role': ChatParticipant.ROLE_CLIENT}
            )
            cache.set(mapping_key, thread.id, timeout=None)
            logger.info(f"Created ChatThread {thread.id} for SupportTicket {ticket_id}")
            return thread
    except Exception as e:
        logger.exception(f"Error in handle_ticket_created: {e}")
        return None

def handle_message_sent(payload):
    """
    Handles 'message_sent' event:
    - only process support messages
    - find ChatThread via mapping
    - create Message in chat: text = payload["text"], sender = correct user/staff, thread = thread
    - fallback: if thread not found -> create one
    """
    try:
        # only process support messages (must have ticket_id)
        ticket_id = payload.get('ticket_id')
        if not ticket_id:
            return None
            
        # no duplicate messages (use support message_id for deduplication)
        support_message_id = payload.get('message_id')
        if support_message_id:
            msg_cache_key = f"support_msg_processed:{support_message_id}"
            if cache.get(msg_cache_key):
                return None
            cache.set(msg_cache_key, True, timeout=3600*24)

        mapping_key = f"support_ticket_thread_map:{ticket_id}"
        thread_id = cache.get(mapping_key)
        
        thread = None
        if thread_id:
            thread = ChatThread.objects.filter(id=thread_id).first()
            
        if not thread:
            # fallback: if thread not found -> create one
            try:
                from support.models import SupportTicket
                ticket = SupportTicket.objects.select_related('user').filter(id=ticket_id).first()
                if ticket:
                    thread = handle_ticket_created({
                        'user': ticket.user,
                        'ticket_id': ticket.id
                    })
            except (ImportError, Exception) as e:
                logger.error(f"Could not find SupportTicket for fallback: {e}")
            
        if not thread:
            logger.warning(f"Could not find or create ChatThread for SupportTicket {ticket_id}")
            return None
            
        sender = payload.get('user')
        text = payload.get('text') or payload.get('message')
        
        if not sender or not text:
            logger.warning(f"handle_message_sent: Missing sender or text in payload: {payload}")
            return None

        with transaction.atomic():
            # Ensure sender is participant
            role = ChatParticipant.ROLE_CLIENT
            if sender.is_staff or sender.is_superuser:
                role = ChatParticipant.ROLE_STAFF
                
            ChatParticipant.objects.get_or_create(
                thread=thread,
                user=sender,
                defaults={'role': role}
            )
            
            message = ChatMessage.objects.create(
                thread=thread,
                sender=sender,
                text=text
            )
            logger.info(f"Created ChatMessage {message.id} from SupportMessage in thread {thread.id}")
            return message
    except Exception as e:
        logger.exception(f"Error in handle_message_sent: {e}")
        return None
