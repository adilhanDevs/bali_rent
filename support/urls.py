from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminExternalContactLinkViewSet,
    AdminSupportMessageViewSet,
    AdminSupportTicketViewSet,
    ExternalContactLinkViewSet,
    SupportMessageViewSet,
    SupportTicketViewSet,
)

public_router = DefaultRouter()
public_router.register(r"support/tickets", SupportTicketViewSet, basename="support-ticket")
public_router.register(r"support/messages", SupportMessageViewSet, basename="support-message")
public_router.register(r"support/contact-links", ExternalContactLinkViewSet, basename="support-contact-link")

admin_router = DefaultRouter()
admin_router.register(r"tickets", AdminSupportTicketViewSet, basename="admin-support-ticket")
admin_router.register(r"messages", AdminSupportMessageViewSet, basename="admin-support-message")
admin_router.register(r"contact-links", AdminExternalContactLinkViewSet, basename="admin-support-contact-link")

urlpatterns = [
    path("", include(public_router.urls)),
    path("admin/support/", include(admin_router.urls)),
]
