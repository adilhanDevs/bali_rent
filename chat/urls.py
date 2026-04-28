from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminChatAttachmentViewSet,
    AdminChatMessageViewSet,
    AdminChatParticipantViewSet,
    AdminChatThreadViewSet,
    AdminQuickReplyViewSet,
    ChatAttachmentViewSet,
    ChatMessageViewSet,
    ChatThreadViewSet,
    QuickReplyViewSet,
)

public_router = DefaultRouter()
public_router.register(r'chat/threads', ChatThreadViewSet, basename='chat-thread')
public_router.register(r'chat/messages', ChatMessageViewSet, basename='chat-message')
public_router.register(r'chat/attachments', ChatAttachmentViewSet, basename='chat-attachment')
public_router.register(r'chat/quick-replies', QuickReplyViewSet, basename='chat-quick-reply')

admin_router = DefaultRouter()
admin_router.register(r'threads', AdminChatThreadViewSet, basename='admin-chat-thread')
admin_router.register(r'participants', AdminChatParticipantViewSet, basename='admin-chat-participant')
admin_router.register(r'messages', AdminChatMessageViewSet, basename='admin-chat-message')
admin_router.register(r'attachments', AdminChatAttachmentViewSet, basename='admin-chat-attachment')
admin_router.register(r'quick-replies', AdminQuickReplyViewSet, basename='admin-chat-quick-reply')

urlpatterns = [
    path('', include(public_router.urls)),
    path('admin/chat/', include(admin_router.urls)),
]
