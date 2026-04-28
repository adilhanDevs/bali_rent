from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import ChatAttachment, ChatMessage, ChatParticipant, ChatThread, QuickReply
from .serializers import (
    ChatAttachmentSerializer,
    ChatMessageSerializer,
    ChatParticipantSerializer,
    ChatThreadSerializer,
    QuickReplySerializer,
)


class ChatPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsChatAdminManagerOrStaffReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.role in {'admin', 'manager'}:
            return True
        if user.role == 'staff':
            return request.method in permissions.SAFE_METHODS
        return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsThreadParticipantOrReadOnlyQuickReply(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if getattr(view, 'basename', '') == 'chat-quick-reply':
            if request.method in permissions.SAFE_METHODS:
                return True
            return user.is_superuser or user.role in {'admin', 'manager'}

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(view, 'basename', '') == 'chat-quick-reply':
            if request.method in permissions.SAFE_METHODS:
                return True
            return user.is_superuser or user.role in {'admin', 'manager'}

        if isinstance(obj, ChatThread):
            thread = obj
        elif isinstance(obj, ChatParticipant):
            thread = obj.thread
        elif isinstance(obj, ChatMessage):
            thread = obj.thread
        elif isinstance(obj, ChatAttachment):
            thread = obj.message.thread
        else:
            return False

        return ChatParticipant.objects.filter(thread=thread, user=user).exists()


class BasePublicChatViewSet(viewsets.ModelViewSet):
    permission_classes = [IsThreadParticipantOrReadOnlyQuickReply]
    pagination_class = ChatPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class BaseAdminChatViewSet(viewsets.ModelViewSet):
    permission_classes = [IsChatAdminManagerOrStaffReadOnly]
    pagination_class = ChatPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class ChatThreadViewSet(BasePublicChatViewSet):
    queryset = ChatThread.objects.prefetch_related('participants__user', 'messages__sender', 'messages__attachments')
    serializer_class = ChatThreadSerializer
    filterset_fields = ['status']
    search_fields = ['title', 'participants__user__full_name', 'participants__user__email']
    ordering_fields = ['created_at', 'updated_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        return queryset.filter(participants__user=user).distinct()


class ChatMessageViewSet(BasePublicChatViewSet):
    queryset = ChatMessage.objects.select_related('thread', 'sender').prefetch_related('attachments')
    serializer_class = ChatMessageSerializer
    filterset_fields = ['thread']
    search_fields = ['text', 'sender__full_name', 'sender__email']
    ordering_fields = ['created_at', 'updated_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        return queryset.filter(thread__participants__user=user).distinct()

    def perform_create(self, serializer):
        serializer.save(sender=serializer.validated_data.get('sender', self.request.user))


class ChatAttachmentViewSet(BasePublicChatViewSet):
    queryset = ChatAttachment.objects.select_related('message__thread', 'uploaded_by')
    serializer_class = ChatAttachmentSerializer
    filterset_fields = ['message']
    search_fields = ['original_name', 'uploaded_by__full_name', 'uploaded_by__email']
    ordering_fields = ['created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        return queryset.filter(message__thread__participants__user=user).distinct()

    def perform_create(self, serializer):
        serializer.save(uploaded_by=serializer.validated_data.get('uploaded_by', self.request.user))


class QuickReplyViewSet(BasePublicChatViewSet):
    queryset = QuickReply.objects.select_related('created_by')
    serializer_class = QuickReplySerializer
    filterset_fields = ['is_active']
    search_fields = ['title', 'text']
    ordering_fields = ['title', 'created_at', 'updated_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.role in {'admin', 'manager', 'staff'}:
            return queryset
        return queryset.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AdminChatThreadViewSet(BaseAdminChatViewSet):
    queryset = ChatThread.objects.prefetch_related('participants__user', 'messages__sender', 'messages__attachments')
    serializer_class = ChatThreadSerializer
    filterset_fields = ['status']
    search_fields = ['title', 'participants__user__full_name', 'participants__user__email']
    ordering_fields = ['created_at', 'updated_at']


class AdminChatParticipantViewSet(BaseAdminChatViewSet):
    queryset = ChatParticipant.objects.select_related('thread', 'user')
    serializer_class = ChatParticipantSerializer
    filterset_fields = ['thread', 'role']
    search_fields = ['user__full_name', 'user__email', 'thread__title']
    ordering_fields = ['joined_at']


class AdminChatMessageViewSet(BaseAdminChatViewSet):
    queryset = ChatMessage.objects.select_related('thread', 'sender').prefetch_related('attachments')
    serializer_class = ChatMessageSerializer
    filterset_fields = ['thread', 'sender']
    search_fields = ['text', 'sender__full_name', 'sender__email', 'thread__title']
    ordering_fields = ['created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(sender=serializer.validated_data.get('sender', self.request.user))


class AdminChatAttachmentViewSet(BaseAdminChatViewSet):
    queryset = ChatAttachment.objects.select_related('message__thread', 'uploaded_by')
    serializer_class = ChatAttachmentSerializer
    filterset_fields = ['message', 'uploaded_by']
    search_fields = ['original_name', 'uploaded_by__full_name', 'uploaded_by__email']
    ordering_fields = ['created_at']

    def perform_create(self, serializer):
        serializer.save(uploaded_by=serializer.validated_data.get('uploaded_by', self.request.user))


class AdminQuickReplyViewSet(BaseAdminChatViewSet):
    queryset = QuickReply.objects.select_related('created_by')
    serializer_class = QuickReplySerializer
    filterset_fields = ['is_active']
    search_fields = ['title', 'text']
    ordering_fields = ['title', 'created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
