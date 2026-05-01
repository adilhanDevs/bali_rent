from rest_framework import viewsets, permissions, response
from rest_framework.decorators import action
from .dev2_metrics import get_tickets_count, get_messages_count, get_reviews_count, get_active_users

class IsDev2AnalyticsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_superuser or user.role in {'admin', 'manager'}

class Dev2AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [IsDev2AnalyticsAdmin]

    def list(self, request):
        data = {
            "tickets": get_tickets_count(),
            "messages": get_messages_count(),
            "reviews": get_reviews_count(),
            "active_users": get_active_users()
        }
        return response.Response(data)
