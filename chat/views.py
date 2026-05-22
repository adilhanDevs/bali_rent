from django.db.models import BooleanField, Count, Exists, Max, OuterRef, Q, Subquery, Value
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from notifications.models import Notification

from .models import ChatAttachment, ChatMessage, ChatParticipant, ChatThread, QuickReply
from .serializers import (
    ChatAttachmentSerializer,
    ChatMessageSerializer,
    ChatParticipantSerializer,
    ChatThreadListSerializer,
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


def _resolve_participant_role(user):
    if user.role == 'manager':
        return ChatParticipant.ROLE_MANAGER
    if user.role in {'admin', 'staff'}:
        return ChatParticipant.ROLE_STAFF
    return ChatParticipant.ROLE_CLIENT


def _can_have_unread_support_reply(user):
    return bool(user and user.is_authenticated and not (user.is_staff or user.role in {'admin', 'manager', 'staff'}))


def _annotate_unread_support_reply(queryset, user):
    if not _can_have_unread_support_reply(user):
        return queryset.annotate(has_unread_support_reply=Value(False, output_field=BooleanField()))

    unread_notifications = Notification.objects.filter(
        user=user,
        type='chat_message_from_support',
        is_read=False,
        data_json__thread_id=OuterRef('pk'),
    )
    return queryset.annotate(has_unread_support_reply=Exists(unread_notifications))


def _thread_list_queryset():
    last_message = ChatMessage.objects.filter(thread_id=OuterRef('pk')).order_by('-created_at', '-id')
    return (
        ChatThread.objects.select_related('created_by')
        .prefetch_related('participants__user')
        .annotate(
            message_count=Count('messages', distinct=True),
            last_message_text=Subquery(last_message.values('text')[:1]),
            last_message_created_at=Subquery(last_message.values('created_at')[:1]),
            last_message_sender_name=Subquery(last_message.values('sender__full_name')[:1]),
            last_message_sender_role=Subquery(last_message.values('sender__role')[:1]),
            support_replied_at=Max(
                'messages__created_at',
                filter=Q(messages__sender__is_staff=True) | Q(messages__sender__role__in=['admin', 'manager', 'staff']),
            ),
        )
        .order_by('-updated_at', '-created_at', '-id')
    )


def _thread_detail_queryset():
    return ChatThread.objects.select_related('created_by').prefetch_related(
        'participants__user',
        'messages__sender',
        'messages__attachments',
    ).order_by('-updated_at', '-created_at', '-id')


class ChatThreadViewSet(BasePublicChatViewSet):
    queryset = _thread_detail_queryset()
    serializer_class = ChatThreadSerializer
    filterset_fields = ['status']
    search_fields = ['title', 'participants__user__full_name', 'participants__user__email']
    ordering_fields = ['created_at', 'updated_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ChatThreadListSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = _thread_list_queryset() if self.action == 'list' else _thread_detail_queryset()
        user = self.request.user
        queryset = queryset.filter(participants__user=user).distinct().order_by('-updated_at', '-created_at', '-id')
        return _annotate_unread_support_reply(queryset, user)

    @action(detail=False, methods=['post'], url_path='ensure-support')
    def ensure_support(self, request):
        title = (request.data.get('title') or 'Support Chat').strip() or 'Support Chat'
        thread = (
            ChatThread.objects.filter(
                created_by=request.user,
                participants__user=request.user,
                status=ChatThread.STATUS_OPEN,
            )
            .order_by('-updated_at', '-created_at')
            .first()
        )

        if thread is None:
            thread = ChatThread.objects.create(title=title[:255], created_by=request.user)
            ChatParticipant.objects.create(
                thread=thread,
                user=request.user,
                role=_resolve_participant_role(request.user),
            )

        serializer = ChatThreadSerializer(thread, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='mark-support-replies-read')
    def mark_support_replies_read(self, request, pk=None):
        thread = self.get_object()
        if not _can_have_unread_support_reply(request.user):
            return Response({'updated': 0})

        updated = Notification.objects.filter(
            user=request.user,
            type='chat_message_from_support',
            is_read=False,
            data_json__thread_id=thread.pk,
        ).update(is_read=True)
        return Response({'updated': updated})


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
        message = serializer.save(sender=serializer.validated_data.get('sender', self.request.user))
        from notifications.services import NotificationService

        NotificationService.notify_chat_message(message)


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
    queryset = _thread_detail_queryset()
    serializer_class = ChatThreadSerializer
    filterset_fields = ['status']
    search_fields = ['title', 'participants__user__full_name', 'participants__user__email']
    ordering_fields = ['created_at', 'updated_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ChatThreadListSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        if self.action == 'list':
            return _thread_list_queryset()
        return _thread_detail_queryset().order_by('-updated_at', '-created_at', '-id')


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
        message = serializer.save(sender=serializer.validated_data.get('sender', self.request.user))
        from notifications.services import NotificationService

        NotificationService.notify_chat_message(message)


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
