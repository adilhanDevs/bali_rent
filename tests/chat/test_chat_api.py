from concurrent.futures import ThreadPoolExecutor
import time

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connections
from django.db import OperationalError

from chat.models import ChatAttachment, ChatMessage, ChatParticipant, ChatThread, QuickReply


pytestmark = pytest.mark.django_db


@pytest.fixture
def other_client_user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        username="other-chat-client",
        email="other-chat-client@example.com",
        password="testpass123",
        full_name="Other Chat Client",
        phone="+996555000333",
        role="client",
    )


@pytest.fixture
def thread(user, manager_user):
    thread = ChatThread.objects.create(title="Support Thread", created_by=user, status=ChatThread.STATUS_OPEN)
    ChatParticipant.objects.create(thread=thread, user=user, role=ChatParticipant.ROLE_CLIENT)
    ChatParticipant.objects.create(thread=thread, user=manager_user, role=ChatParticipant.ROLE_MANAGER)
    return thread


@pytest.fixture
def message(thread, user):
    return ChatMessage.objects.create(thread=thread, sender=user, text="Initial message")


def test_chat_thread_crud_owner_access_and_pagination(auth_client, manager_user, user, thread):
    another_thread = ChatThread.objects.create(title="Second Thread", created_by=user, status=ChatThread.STATUS_OPEN)
    ChatParticipant.objects.create(thread=another_thread, user=user, role=ChatParticipant.ROLE_CLIENT)
    ChatParticipant.objects.create(thread=another_thread, user=manager_user, role=ChatParticipant.ROLE_MANAGER)

    list_response = auth_client.get("/api/v1/chat/threads/?page_size=1")
    assert list_response.status_code == 200
    assert list_response.data["count"] == 2
    assert len(list_response.data["results"]) == 1
    assert list_response.data["next"]

    create_response = auth_client.post(
        "/api/v1/chat/threads/",
        {
            "title": "New Client Thread",
            "status": ChatThread.STATUS_OPEN,
            "participant_ids": [manager_user.id],
        },
        format="json",
    )
    assert create_response.status_code == 201
    created_id = create_response.data["id"]
    assert ChatParticipant.objects.filter(thread_id=created_id, user=user).exists()

    detail_response = auth_client.get(f"/api/v1/chat/threads/{created_id}/")
    assert detail_response.status_code == 200

    patch_response = auth_client.patch(
        f"/api/v1/chat/threads/{created_id}/",
        {"title": "Renamed Thread", "status": ChatThread.STATUS_CLOSED},
        format="json",
    )
    assert patch_response.status_code == 200
    assert patch_response.data["status"] == ChatThread.STATUS_CLOSED

    delete_response = auth_client.delete(f"/api/v1/chat/threads/{created_id}/")
    assert delete_response.status_code == 204


def test_chat_message_and_attachment_validation_and_non_participant_access(
    api_client,
    auth_client,
    other_client_user,
    thread,
    message,
):
    unauthorized = api_client.get("/api/v1/chat/threads/")
    assert unauthorized.status_code in {401, 403}

    other_client = api_client
    other_client.force_authenticate(user=other_client_user)

    hidden_thread = other_client.get(f"/api/v1/chat/threads/{thread.id}/")
    assert hidden_thread.status_code == 404

    invalid_message = other_client.post(
        "/api/v1/chat/messages/",
        {"thread_id": thread.id, "text": "I should not be here"},
        format="json",
    )
    assert invalid_message.status_code == 400
    assert "sender" in invalid_message.data

    valid_message = auth_client.post(
        "/api/v1/chat/messages/",
        {"thread_id": thread.id, "text": "Owner reply"},
        format="json",
    )
    assert valid_message.status_code == 201
    message_id = valid_message.data["id"]

    upload_response = auth_client.post(
        "/api/v1/chat/attachments/",
        {
            "message_id": message_id,
            "file": SimpleUploadedFile("chat.txt", b"hello", content_type="text/plain"),
        },
        format="multipart",
    )
    assert upload_response.status_code == 201
    attachment_id = upload_response.data["id"]

    patch_response = auth_client.patch(
        f"/api/v1/chat/attachments/{attachment_id}/",
        {"original_name": "renamed-chat.txt"},
        format="json",
    )
    assert patch_response.status_code == 200
    assert ChatAttachment.objects.get(pk=attachment_id).original_name == "renamed-chat.txt"

    delete_response = auth_client.delete(f"/api/v1/chat/messages/{message_id}/")
    assert delete_response.status_code == 204


def test_chat_quick_reply_permissions(auth_client, manager_client, staff_client):
    QuickReply.objects.create(title="Greeting", text="Hello", is_active=True, created_by_id=None)

    client_list = auth_client.get("/api/v1/chat/quick-replies/")
    assert client_list.status_code == 200
    assert client_list.data["count"] == 1

    client_create = auth_client.post(
        "/api/v1/chat/quick-replies/",
        {"title": "Blocked", "text": "No write", "is_active": True},
        format="json",
    )
    assert client_create.status_code == 403

    staff_create = staff_client.post(
        "/api/v1/chat/quick-replies/",
        {"title": "Staff Blocked", "text": "No write", "is_active": True},
        format="json",
    )
    assert staff_create.status_code == 403

    manager_create = manager_client.post(
        "/api/v1/chat/quick-replies/",
        {"title": "Approved Reply", "text": "We are on it", "is_active": True},
        format="json",
    )
    assert manager_create.status_code == 201


def test_admin_chat_endpoints_permissions_and_crud(
    admin_client,
    admin_user,
    manager_client,
    staff_client,
    auth_client,
    manager_user,
    staff_user,
):
    create_thread = manager_client.post(
        "/api/v1/admin/chat/threads/",
        {
            "title": "Admin Thread",
            "status": ChatThread.STATUS_OPEN,
            "participant_ids": [staff_user.id],
        },
        format="json",
    )
    assert create_thread.status_code == 201
    thread_id = create_thread.data["id"]

    participant_create = manager_client.post(
        "/api/v1/admin/chat/participants/",
        {"thread_id": thread_id, "user_id": admin_user.id, "role": ChatParticipant.ROLE_STAFF},
        format="json",
    )
    assert participant_create.status_code == 201

    message_create = manager_client.post(
        "/api/v1/admin/chat/messages/",
        {"thread_id": thread_id, "text": "Manager note"},
        format="json",
    )
    assert message_create.status_code == 201
    admin_message_id = message_create.data["id"]

    attachment_create = manager_client.post(
        "/api/v1/admin/chat/attachments/",
        {
            "message_id": admin_message_id,
            "file": SimpleUploadedFile("admin.txt", b"admin body", content_type="text/plain"),
        },
        format="multipart",
    )
    assert attachment_create.status_code == 201

    quick_reply_create = admin_client.post(
        "/api/v1/admin/chat/quick-replies/",
        {"title": "Admin Reply", "text": "Handled", "is_active": True},
        format="json",
    )
    assert quick_reply_create.status_code == 201

    staff_list = staff_client.get("/api/v1/admin/chat/threads/")
    assert staff_list.status_code == 200

    staff_write = staff_client.post(
        "/api/v1/admin/chat/threads/",
        {"title": "Forbidden", "status": ChatThread.STATUS_OPEN, "participant_ids": [manager_user.id]},
        format="json",
    )
    assert staff_write.status_code == 403

    client_forbidden = auth_client.get("/api/v1/admin/chat/threads/")
    assert client_forbidden.status_code == 403

    missing_detail = admin_client.get("/api/v1/admin/chat/participants/999999/")
    assert missing_detail.status_code == 404


def test_chat_404_duplicate_participant_and_invalid_payloads(
    admin_client,
    auth_client,
    manager_user,
    thread,
    other_client_user,
):
    missing_message = auth_client.get("/api/v1/chat/messages/999999/")
    assert missing_message.status_code == 404

    duplicate_participant = admin_client.post(
        "/api/v1/admin/chat/participants/",
        {"thread_id": thread.id, "user_id": manager_user.id, "role": ChatParticipant.ROLE_MANAGER},
        format="json",
    )
    assert duplicate_participant.status_code == 400

    empty_message = auth_client.post("/api/v1/chat/messages/", {}, format="json")
    assert empty_message.status_code == 400
    assert "thread_id" in empty_message.data

    bad_attachment = auth_client.post(
        "/api/v1/chat/attachments/",
        {"message_id": 999999},
        format="multipart",
    )
    assert bad_attachment.status_code == 400
    assert "message_id" in bad_attachment.data

    too_long_quick_reply = admin_client.post(
        "/api/v1/admin/chat/quick-replies/",
        {"title": "x" * 101, "text": "Too long", "is_active": True},
        format="json",
    )
    assert too_long_quick_reply.status_code == 400
    assert "title" in too_long_quick_reply.data

    foreign_thread_message = auth_client.post(
        "/api/v1/chat/messages/",
        {"thread_id": thread.id, "sender_id": other_client_user.id, "text": "Escalation attempt"},
        format="json",
    )
    assert foreign_thread_message.status_code == 400
    assert "sender" in foreign_thread_message.data


@pytest.mark.django_db(transaction=True)
def test_chat_message_create_rollback_on_validation_error(auth_client, other_client_user, thread):
    before_count = ChatMessage.objects.count()

    response = auth_client.post(
        "/api/v1/chat/messages/",
        {"thread_id": thread.id, "sender_id": other_client_user.id, "text": "Broken sender"},
        format="json",
    )
    assert response.status_code == 400
    assert ChatMessage.objects.count() == before_count


@pytest.mark.django_db(transaction=True)
def test_chat_concurrent_message_posts_create_distinct_messages(user, manager_user, thread):
    def post_message(actor, text):
        from rest_framework.test import APIClient

        for attempt in range(3):
            client = APIClient()
            client.force_authenticate(user=actor)
            try:
                response = client.post(
                    "/api/v1/chat/messages/",
                    {"thread_id": thread.id, "text": text},
                    format="json",
                )
                return response.status_code
            except OperationalError:
                if attempt == 2:
                    raise
                time.sleep(0.05)
            finally:
                connections.close_all()

    start_count = ChatMessage.objects.filter(thread=thread).count()
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(
            pool.map(
                lambda args: post_message(*args),
                [(user, "Concurrent 1"), (manager_user, "Concurrent 2")],
            )
        )

    assert statuses == [201, 201]
    texts = list(ChatMessage.objects.filter(thread=thread).values_list("text", flat=True))
    assert len(texts) >= start_count + 2
    assert "Concurrent 1" in texts
    assert "Concurrent 2" in texts


def test_chat_thread_list_query_count(auth_client, thread, django_assert_num_queries):
    ChatMessage.objects.create(thread=thread, sender=thread.created_by, text="More messages")

    with django_assert_num_queries(8, exact=False):
        response = auth_client.get("/api/v1/chat/threads/")

    assert response.status_code == 200


def test_chat_thread_participant_validation_and_update_branch(auth_client, manager_user, other_client_user, thread):
    duplicate_participants = auth_client.post(
        "/api/v1/chat/threads/",
        {"title": "Dup thread", "participant_ids": [manager_user.id, manager_user.id]},
        format="json",
    )
    assert duplicate_participants.status_code == 400
    assert "participant_ids" in duplicate_participants.data

    patch_participants = auth_client.patch(
        f"/api/v1/chat/threads/{thread.id}/",
        {"participant_ids": [other_client_user.id]},
        format="json",
    )
    assert patch_participants.status_code == 200
    assert ChatParticipant.objects.filter(thread=thread, user=other_client_user).exists()
    assert ChatParticipant.objects.filter(thread=thread, user=manager_user).exists() is False


def test_chat_serializer_update_error_paths(admin_client, auth_client, other_client_user, manager_user, thread):
    message = ChatMessage.objects.create(thread=thread, sender=manager_user, text="Manager message")
    attachment = ChatAttachment.objects.create(
        message=message,
        uploaded_by=manager_user,
        file=SimpleUploadedFile("m.txt", b"body", content_type="text/plain"),
    )

    invalid_message_patch = auth_client.patch(
        f"/api/v1/chat/messages/{message.id}/",
        {"sender_id": other_client_user.id},
        format="json",
    )
    assert invalid_message_patch.status_code == 400
    assert "sender" in invalid_message_patch.data

    invalid_attachment_patch = admin_client.patch(
        f"/api/v1/admin/chat/attachments/{attachment.id}/",
        {"uploaded_by_id": other_client_user.id},
        format="json",
    )
    assert invalid_attachment_patch.status_code == 400
    assert "uploaded_by" in invalid_attachment_patch.data
