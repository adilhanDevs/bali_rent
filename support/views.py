from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import ExternalContactLink, SupportMessage, SupportTicket
from .permissions import IsSupportAdminManagerOrStaffReadOnly, IsSupportTicketOwnerOrTeam, is_support_team
from .serializers import (
    ExternalContactLinkSerializer,
    SupportMessageSerializer,
    SupportTicketSerializer,
)


class SupportPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class BasePublicSupportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSupportTicketOwnerOrTeam]
    pagination_class = SupportPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class BaseAdminSupportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSupportAdminManagerOrStaffReadOnly]
    pagination_class = SupportPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class SupportTicketViewSet(BasePublicSupportViewSet):
    queryset = SupportTicket.objects.select_related("user").prefetch_related("messages__sender")
    serializer_class = SupportTicketSerializer
    filterset_fields = ["status", "channel"]
    search_fields = ["subject", "user__full_name", "user__email"]
    ordering_fields = ["created_at", "closed_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_support_team(self.request.user):
            return queryset
        return queryset.filter(user=self.request.user)


class SupportMessageViewSet(BasePublicSupportViewSet):
    queryset = SupportMessage.objects.select_related("ticket__user", "sender")
    serializer_class = SupportMessageSerializer
    filterset_fields = ["ticket", "sender"]
    search_fields = ["message", "sender__full_name", "sender__email", "ticket__subject"]
    ordering_fields = ["created_at"]
    ordering = ["created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_support_team(self.request.user):
            return queryset
        return queryset.filter(ticket__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(sender=serializer.validated_data.get("sender", self.request.user))


class ExternalContactLinkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExternalContactLink.objects.all()
    serializer_class = ExternalContactLinkSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SupportPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["code", "title", "phone"]
    ordering_fields = ["sort_order", "title"]
    ordering = ["sort_order", "title"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_support_team(self.request.user):
            return queryset
        return queryset.filter(is_active=True)


class AdminSupportTicketViewSet(BaseAdminSupportViewSet):
    queryset = SupportTicket.objects.select_related("user").prefetch_related("messages__sender")
    serializer_class = SupportTicketSerializer
    filterset_fields = ["status", "channel", "user"]
    search_fields = ["subject", "user__full_name", "user__email"]
    ordering_fields = ["created_at", "closed_at", "status"]
    ordering = ["-created_at"]


class AdminSupportMessageViewSet(BaseAdminSupportViewSet):
    queryset = SupportMessage.objects.select_related("ticket__user", "sender")
    serializer_class = SupportMessageSerializer
    filterset_fields = ["ticket", "sender"]
    search_fields = ["message", "sender__full_name", "sender__email", "ticket__subject"]
    ordering_fields = ["created_at"]
    ordering = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(sender=serializer.validated_data.get("sender", self.request.user))


class AdminExternalContactLinkViewSet(BaseAdminSupportViewSet):
    queryset = ExternalContactLink.objects.all()
    serializer_class = ExternalContactLinkSerializer
    filterset_fields = ["is_active"]
    search_fields = ["code", "title", "phone"]
    ordering_fields = ["sort_order", "title"]
    ordering = ["sort_order", "title"]
