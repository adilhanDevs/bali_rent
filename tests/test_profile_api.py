import pytest


@pytest.mark.django_db
def test_profile_patch_updates_user_and_profile_fields(auth_client, user):
    response = auth_client.patch(
        "/api/v1/profile/",
        {
            "full_name": "Updated Rider",
            "phone": "+628123456789",
            "country": "Indonesia",
            "language": "ru",
            "currency": "EUR",
        },
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    user.profile.refresh_from_db()

    assert user.full_name == "Updated Rider"
    assert user.phone == "+628123456789"
    assert user.profile.country == "Indonesia"
    assert user.profile.preferred_language == "ru"
    assert user.profile.preferred_currency == "EUR"


@pytest.mark.django_db
def test_profile_patch_rejects_unsupported_currency(auth_client):
    response = auth_client.patch(
        "/api/v1/profile/",
        {
          "currency": "GBP",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "currency" in response.data
