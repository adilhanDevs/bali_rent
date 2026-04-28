from rest_framework.routers import DefaultRouter

from .views import (
    CustomerInteractionViewSet,
    CustomerNoteViewSet,
    CustomerProfileViewSet,
    CustomerSegmentViewSet,
)

router = DefaultRouter()
router.register(r'customer-segments', CustomerSegmentViewSet, basename='crm-customer-segment')
router.register(r'customer-profiles', CustomerProfileViewSet, basename='crm-customer-profile')
router.register(r'customer-notes', CustomerNoteViewSet, basename='crm-customer-note')
router.register(r'customer-interactions', CustomerInteractionViewSet, basename='crm-customer-interaction')

urlpatterns = router.urls
