from .models import AnalyticsEvent

class AnalyticsService:
    @staticmethod
    def track_event(user, event_name, properties=None, payload=None, ip_address=None, user_agent=None):
        event_payload = payload if payload is not None else (properties or {})
        return AnalyticsEvent.objects.create(
            user=user,
            event_name=event_name,
            payload=event_payload,
            ip_address=ip_address,
            user_agent=user_agent
        )
