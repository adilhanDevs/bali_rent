import json
import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Avg

from crm.models import CustomerProfile, CustomerInteraction, CustomerSegment

logger = logging.getLogger(__name__)

def get_customer_rating_metrics(profile):
    """
    Calculates average rating from review interactions.
    """
    interactions = profile.interactions.filter(interaction_type="review")
    ratings = []
    for interaction in interactions:
        try:
            payload = json.loads(interaction.description)
            rating = payload.get("rating")
            if rating is not None:
                ratings.append(float(rating))
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    
    if not ratings:
        return 0.0
    
    return sum(ratings) / len(ratings)

def _sync_profile_rating(profile):
    """
    Computes avg_rating, saves it to profile, and updates segment if needed.
    """
    avg_rating = get_customer_rating_metrics(profile)
    profile.avg_rating = avg_rating
    update_fields = ["avg_rating", "updated_at"]
    
    # Logic for VIP priority based on rating
    if avg_rating >= 4.5:
        vip_segment, _ = CustomerSegment.objects.get_or_create(
            code="vip",
            defaults={"name": "VIP", "discount_percent": Decimal("10.00")}
        )
        if profile.segment_id != vip_segment.id:
            profile.segment = vip_segment
            update_fields.append("segment")
    
    profile.save(update_fields=update_fields)
    return profile

@transaction.atomic
def handle_review_created(payload):
    """
    Handles 'review_created' event:
    - Records review interaction
    - Calculates average rating
    - Updates segment if rating is high
    """
    profile = _profile_from_payload(payload)
    if profile is None:
        user = payload.get("user")
        if user and hasattr(user, "id"):
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
        else:
            return None

    rating = payload.get("rating")
    if rating is None:
        return None

    interaction_payload = {
        "review_id": payload.get("review_id"),
        "rating": rating,
        "comment": payload.get("comment", ""),
    }
    
    CustomerInteraction.objects.create(
        customer=profile,
        interaction_type="review",
        description=json.dumps(interaction_payload, sort_keys=True),
    )
    
    # Update and return profile with metrics
    profile = _sync_profile_rating(profile)
    
    # Attach financial metrics (computed only)
    try:
        from crm.services.events_handlers import _attach_metrics
        profile = _attach_metrics(profile)
    except ImportError:
        pass
    
    return profile

def _profile_from_payload(payload):
    user = payload.get("user")
    user_id = getattr(user, "id", None) or payload.get("user_id")
    if not user_id:
        return None
    return CustomerProfile.objects.filter(user_id=user_id).first()
