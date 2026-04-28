from .models import AnalyticsEvent

class AnalyticsService:
    @staticmethod
    def track_event(user, event_name, properties=None, ip_address=None, user_agent=None):
        return AnalyticsEvent.objects.create(
            user=user,
            event_name=event_name,
            properties=properties or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
