import pytest
from rest_framework.test import APIClient


pytestmark = pytest.mark.django_db


def test_user_can_change_own_password(api_client, staff_user):
    staff_user.set_password("OldStrongPassword123!")
    staff_user.save(update_fields=["password"])
    api_client.force_authenticate(user=staff_user)

    response = api_client.post(
        "/api/v1/users/me/change-password/",
        {
            "current_password": "OldStrongPassword123!",
            "new_password": "NewStrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 200
    staff_user.refresh_from_db()
    assert staff_user.check_password("NewStrongPassword123!")


def test_user_cannot_change_own_password_with_wrong_current_password(api_client, staff_user):
    staff_user.set_password("OldStrongPassword123!")
    staff_user.save(update_fields=["password"])
    api_client.force_authenticate(user=staff_user)

    response = api_client.post(
        "/api/v1/users/me/change-password/",
        {
            "current_password": "WrongPassword123!",
            "new_password": "NewStrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 400
    staff_user.refresh_from_db()
    assert staff_user.check_password("OldStrongPassword123!")


def test_staff_without_team_access_cannot_update_admin_users(staff_client, manager_user):
    response = staff_client.patch(
        f"/api/v1/admin/users/{manager_user.id}/",
        {"full_name": "Should Not Work"},
        format="json",
    )

    assert response.status_code == 403


def test_staff_without_team_access_cannot_set_other_user_password(staff_client, manager_user):
    response = staff_client.post(
        f"/api/v1/admin/users/{manager_user.id}/set-password/",
        {"new_password": "AnotherStrongPassword123!"},
        format="json",
    )

    assert response.status_code == 403


def test_team_access_manager_can_set_staff_password(manager_user, staff_user):
    manager_user.admin_permissions = ["team"]
    manager_user.save(update_fields=["admin_permissions"])

    client = APIClient()
    client.force_authenticate(user=manager_user)

    response = client.post(
        f"/api/v1/admin/users/{staff_user.id}/set-password/",
        {"new_password": "AnotherStrongPassword123!"},
        format="json",
    )

    assert response.status_code == 200
    staff_user.refresh_from_db()
    assert staff_user.check_password("AnotherStrongPassword123!")


def test_admin_can_set_staff_password(admin_client, staff_user):
    response = admin_client.post(
        f"/api/v1/admin/users/{staff_user.id}/set-password/",
        {"new_password": "AdminSetStrongPassword123!"},
        format="json",
    )

    assert response.status_code == 200
    staff_user.refresh_from_db()
    assert staff_user.check_password("AdminSetStrongPassword123!")
