import pytest
from django.contrib.contenttypes.models import ContentType

from audit.models import AdminLoginLog, AuditLog
from audit.services import AuditService
from crm.models import CustomerSegment


pytestmark = pytest.mark.django_db


def test_admin_login_creates_audit_record(client, admin_user):
    response = client.post(
        "/admin/login/?next=/admin/",
        {"username": admin_user.email, "password": "testpass123"},
        HTTP_USER_AGENT="pytest-agent",
        REMOTE_ADDR="127.0.0.9",
    )
    assert response.status_code == 302
    log = AdminLoginLog.objects.latest("created_at")
    assert log.user_id == admin_user.id
    assert log.user_agent == "pytest-agent"
    assert log.ip_address == "127.0.0.9"


def test_admin_audit_endpoints_permissions_and_payload(admin_client, auth_client, admin_user):
    segment = CustomerSegment.objects.create(code="audit-seg", name="Audit Segment", discount_percent="1.00")
    audit_log = AuditService.log_action(
        user=admin_user,
        obj=segment,
        action="update",
        before_dict={"name": "Old"},
        after_dict={"name": "Audit Segment"},
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert AuditLog.objects.filter(pk=audit_log.id).exists()
    assert ContentType.objects.get_for_model(segment) == audit_log.content_type

    list_response = admin_client.get("/api/v1/admin/audit/")
    assert list_response.status_code == 200
    assert list_response.data["count"] >= 1

    login_logs_response = admin_client.get("/api/v1/admin/security/logins/")
    assert login_logs_response.status_code == 200

    forbidden = auth_client.get("/api/v1/admin/audit/")
    assert forbidden.status_code == 403
