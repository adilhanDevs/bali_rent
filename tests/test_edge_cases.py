import pytest


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/admin/crm/customer-segments/", b'{"code": "broken"'),
        ("/api/v1/chat/threads/", b'{"title": "broken"'),
        ("/api/v1/loyalty/accounts/", b'{"customer_id": 1'),
        ("/api/v1/reviews/", b'{"booking": 1'),
    ],
)
def test_invalid_json_returns_400_for_core_endpoints(admin_client, path, payload):
    response = admin_client.generic("POST", path, payload, content_type="application/json")
    assert response.status_code == 400


def test_empty_payloads_fail_fast(admin_client, manager_client, auth_client):
    assert admin_client.post("/api/v1/admin/tasks/staff-tasks/", {}, format="json").status_code == 400
    assert manager_client.post("/api/v1/loyalty/transactions/", {}, format="json").status_code == 400
    assert auth_client.post("/api/v1/chat/messages/", {}, format="json").status_code == 400
    assert auth_client.post("/api/v1/reviews/", {}, format="json").status_code == 400

