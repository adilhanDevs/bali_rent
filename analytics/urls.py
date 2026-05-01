from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_dev2 import Dev2AnalyticsViewSet

router = DefaultRouter()
router.register(r'', Dev2AnalyticsViewSet, basename='admin-analytics-dev2')

urlpatterns = [
    path('dev2/', Dev2AnalyticsViewSet.as_view({'get': 'list'}), name='admin-analytics-dev2'),
]
