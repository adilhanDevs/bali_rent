from rest_framework.routers import DefaultRouter

from .views import StaffTaskViewSet, TaskChecklistItemViewSet, TaskCommentViewSet

router = DefaultRouter()
router.register(r'staff-tasks', StaffTaskViewSet, basename='staff-task')
router.register(r'checklist-items', TaskChecklistItemViewSet, basename='task-checklist-item')
router.register(r'comments', TaskCommentViewSet, basename='task-comment')

urlpatterns = router.urls
