from copy import deepcopy
import importlib.util
from pathlib import Path

from analytics.models import AnalyticsEvent


SUPPORTED_EVENTS = {
    "booking_created",
    "payment_completed",
    "ticket_created",
    "message_sent",
    "review_created",
}

RESERVED_PAYLOAD_KEYS = {
    "user",
    "session_id",
    "device_id",
    "ip_address",
    "user_agent",
}


class EventService:
    @staticmethod
    def _load_notifications_handlers_module():
        handlers_path = Path(__file__).resolve().parents[1] / "notifications" / "services" / "event_handlers.py"
        if not handlers_path.exists():
            return None

        spec = importlib.util.spec_from_file_location("notifications_event_handlers", handlers_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _dispatch_to_integrations(event_name, payload):
        # CRM Integration
        try:
            from crm.services.events_handlers import (
                handle_booking_created,
                handle_payment_completed,
            )
            from crm.services.review_handlers import handle_review_created
            handlers = {
                "booking_created": handle_booking_created,
                "payment_completed": handle_payment_completed,
                "review_created": handle_review_created,
            }
            handler = handlers.get(event_name)
            if handler is not None:
                handler(payload or {})
        except Exception:
            pass

        # Notifications Integration
        try:
            notifications_handlers = EventService._load_notifications_handlers_module()
            if notifications_handlers is not None:
                notification_handlers = {
                    "booking_created": notifications_handlers.handle_booking_created,
                    "payment_completed": notifications_handlers.handle_payment_completed,
                    "ticket_created": notifications_handlers.handle_ticket_created,
                    "message_sent": notifications_handlers.handle_message_sent,
                }
                notification_handler = notification_handlers.get(event_name)
                if notification_handler is not None:
                    notification_handler(payload or {})
        except Exception:
            pass

        # Loyalty Integration
        try:
            from loyalty.services.event_handlers import handle_payment_completed as loyalty_payment_completed
            loyalty_handlers = {
                "payment_completed": loyalty_payment_completed,
            }
            loyalty_handler = loyalty_handlers.get(event_name)
            if loyalty_handler is not None:
                loyalty_handler(payload or {})
        except Exception:
            pass

        # Chat Integration
        try:
            from chat.services.event_handlers import (
                handle_ticket_created as chat_handle_ticket,
                handle_message_sent as chat_handle_message,
            )
            chat_handlers = {
                "ticket_created": chat_handle_ticket,
                "message_sent": chat_handle_message,
            }
            chat_handler = chat_handlers.get(event_name)
            if chat_handler:
                chat_handler(payload or {})
        except Exception:
            pass

    @staticmethod
    def emit_event(event_name, payload):
        if event_name not in SUPPORTED_EVENTS:
            raise ValueError(f"Unsupported event: {event_name}")

        if payload is None:
            payload = {}

        if not isinstance(payload, dict):
            raise ValueError("Event payload must be a dictionary.")

        safe_payload = deepcopy(payload)
        user = safe_payload.pop("user", None)
        session_id = safe_payload.pop("session_id", None)
        device_id = safe_payload.pop("device_id", None)
        ip_address = safe_payload.pop("ip_address", None)
        user_agent = safe_payload.pop("user_agent", None)

        if user is not None and not hasattr(user, "pk"):
            raise ValueError("Payload user must be a Django user instance.")

        event = AnalyticsEvent.objects.create(
            user=user,
            session_id=session_id,
            device_id=device_id,
            event_name=event_name,
            payload=safe_payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        EventService._dispatch_to_integrations(event_name, payload)
        return event


def emit_event(event_name, payload=None):
    return EventService.emit_event(event_name=event_name, payload=payload)
