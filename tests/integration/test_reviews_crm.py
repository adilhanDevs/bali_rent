import pytest
from events.services import emit_event
from crm.models import CustomerProfile, CustomerInteraction, CustomerSegment

pytestmark = pytest.mark.django_db

def test_review_created_updates_crm_rating(user):
    # Ensure profile exists
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    
    emit_event("review_created", {
        "user": user,
        "review_id": 1,
        "rating": 5,
        "comment": "Excellent!"
    })
    
    profile.refresh_from_db()
    assert profile.avg_rating == 5.0
    # 5.0 >= 4.5 -> VIP
    assert profile.segment.code == "vip"

def test_multiple_reviews_calculate_average(user):
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    
    # Use ratings that don't trigger VIP first to avoid stickiness issues in this simple test
    emit_event("review_created", {"user": user, "review_id": 10, "rating": 4})
    emit_event("review_created", {"user": user, "review_id": 11, "rating": 2})
    
    profile.refresh_from_db()
    # Average (4+2)/2 = 3.0
    assert profile.avg_rating == 3.0
    assert profile.segment is None or profile.segment.code != "vip"

def test_high_rating_gives_vip_priority(user):
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    
    emit_event("review_created", {"user": user, "review_id": 20, "rating": 5})
    
    profile.refresh_from_db()
    assert profile.avg_rating == 5.0
    assert profile.segment.code == "vip"

def test_bad_payload_handling():
    # Should not crash
    emit_event("review_created", {"something": "else"})
    emit_event("review_created", {"user": None, "rating": 5})
    # Should be safe
