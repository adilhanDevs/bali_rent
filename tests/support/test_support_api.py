import pytest

from support.models import ExternalContactLink, SupportMessage, SupportTicket


pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.support_test_urls")]


@pytest.fixture
def support_ticket(user):
    return SupportTicket.objects.create(
        user=user,
        subject="Delivery issue",
        status="open",
        channel="app",
    )


@pytest.fixture
def other_user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        username="support-other",
        email="support-other@example.com",
        password="testpass123",
        full_name="Support Other",
        phone="+996555001234",
        role="client",
    )


def test_support_ticket_public_crud_owner_scope_and_pagination(auth_client, second_user):
    SupportTicket.objects.create(user=second_user, subject="Second", status="open", channel="telegram")
    SupportTicket.objects.create(user=second_user, subject="Third", status="open", channel="whatsapp")

    create_response = auth_client.post(
        "/api/v1/support/tickets/",
        {"subject": "Battery problem", "channel": "app"},
        format="json",
    )
    assert create_response.status_code == 201
    ticket_id = create_response.data["id"]

    list_response = auth_client.get("/api/v1/support/tickets/?page_size=1")
    assert list_response.status_code == 200
    assert list_response.data["count"] == 1
    assert len(list_response.data["results"]) == 1

    detail_response = auth_client.get(f"/api/v1/support/tickets/{ticket_id}/")
    assert detail_response.status_code == 200

    patch_response = auth_client.patch(
        f"/api/v1/support/tickets/{ticket_id}/",
        {"subject": "Battery problem updated"},
        format="json",
    )
    assert patch_response.status_code == 200
    assert patch_response.data["subject"] == "Battery problem updated"

    delete_response = auth_client.delete(f"/api/v1/support/tickets/{ticket_id}/")
    assert delete_response.status_code == 204
    assert SupportTicket.objects.filter(pk=ticket_id).exists() is False


def test_support_ticket_permissions_and_validation(api_client, auth_client, other_user, support_ticket):
    unauthorized = api_client.get("/api/v1/support/tickets/")
    assert unauthorized.status_code in {401, 403}

    foreign_client = api_client
    foreign_client.force_authenticate(user=other_user)

    hidden_detail = foreign_client.get(f"/api/v1/support/tickets/{support_ticket.id}/")
    assert hidden_detail.status_code == 404

    invalid_payload = auth_client.post("/api/v1/support/tickets/", {}, format="json")
    assert invalid_payload.status_code == 400
    assert "subject" in invalid_payload.data

    invalid_status = auth_client.post(
        "/api/v1/support/tickets/",
        {"subject": "Broken", "channel": "app", "status": "closed"},
        format="json",
    )
    assert invalid_status.status_code == 400
    assert "status" in invalid_status.data


def test_support_message_crud_and_ticket_status_transition(auth_client, admin_client, support_ticket):
    create_message = auth_client.post(
        "/api/v1/support/messages/",
        {"ticket_id": support_ticket.id, "message": "Need help asap"},
        format="json",
    )
    assert create_message.status_code == 201
    message_id = create_message.data["id"]

    admin_reply = admin_client.post(
        "/api/v1/admin/support/messages/",
        {"ticket_id": support_ticket.id, "message": "We are checking this now."},
        format="json",
    )
    assert admin_reply.status_code == 201
    support_ticket.refresh_from_db()
    assert support_ticket.status == "in_progress"

    detail_response = auth_client.get(f"/api/v1/support/messages/{message_id}/")
    assert detail_response.status_code == 200

    patch_response = admin_client.patch(
        f"/api/v1/admin/support/messages/{message_id}/",
        {"message": "Updated help request"},
        format="json",
    )
    assert patch_response.status_code == 200

    delete_response = admin_client.delete(f"/api/v1/admin/support/messages/{message_id}/")
    assert delete_response.status_code == 204
    assert SupportMessage.objects.filter(pk=message_id).exists() is False


def test_support_admin_routes_permissions_search_and_filters(
    admin_client,
    staff_client,
    auth_client,
    support_ticket,
):
    SupportTicket.objects.create(user=support_ticket.user, subject="WhatsApp issue", status="closed", channel="whatsapp")

    admin_list = admin_client.get("/api/v1/admin/support/tickets/?search=WhatsApp&status=closed")
    assert admin_list.status_code == 200
    assert admin_list.data["count"] == 1

    staff_list = staff_client.get("/api/v1/admin/support/tickets/")
    assert staff_list.status_code == 200

    staff_write = staff_client.post(
        "/api/v1/admin/support/tickets/",
        {"user_id": support_ticket.user_id, "subject": "Forbidden", "channel": "app"},
        format="json",
    )
    assert staff_write.status_code == 403

    client_forbidden = auth_client.get("/api/v1/admin/support/tickets/")
    assert client_forbidden.status_code == 403


def test_support_contact_links_public_visibility_and_admin_crud(admin_client, auth_client):
    active_link = ExternalContactLink.objects.create(
        code="telegram",
        title="Telegram",
        url="https://t.me/balirent",
        phone="+621111",
        is_active=True,
        sort_order=1,
    )
    ExternalContactLink.objects.create(
        code="legacy",
        title="Legacy",
        url="https://example.com/legacy",
        is_active=False,
        sort_order=2,
    )

    public_list = auth_client.get("/api/v1/support/contact-links/")
    assert public_list.status_code == 200
    assert public_list.data["count"] == 1
    assert public_list.data["results"][0]["id"] == active_link.id

    create_response = admin_client.post(
        "/api/v1/admin/support/contact-links/",
        {
            "code": "whatsapp",
            "title": "WhatsApp",
            "url": "https://wa.me/123456",
            "phone": "+62123456",
            "is_active": True,
            "sort_order": 3,
        },
        format="json",
    )
    assert create_response.status_code == 201
    link_id = create_response.data["id"]

    patch_response = admin_client.patch(
        f"/api/v1/admin/support/contact-links/{link_id}/",
        {"title": "WhatsApp Support"},
        format="json",
    )
    assert patch_response.status_code == 200

    duplicate_response = admin_client.post(
        "/api/v1/admin/support/contact-links/",
        {
            "code": "telegram",
            "title": "Duplicate",
            "url": "https://t.me/duplicate",
            "is_active": True,
        },
        format="json",
    )
    assert duplicate_response.status_code == 400

    delete_response = admin_client.delete(f"/api/v1/admin/support/contact-links/{link_id}/")
    assert delete_response.status_code == 204
