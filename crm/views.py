from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import (
    CustomerInteraction,
    CustomerNote,
    CustomerProfile,
    CustomerSegment,
    StaffTask,
    TaskChecklistItem,
    TaskComment,
)
from .serializers import (
    CustomerInteractionSerializer,
    CustomerNoteSerializer,
    CustomerProfileSerializer,
    CustomerSegmentSerializer,
    StaffTaskChecklistItemSerializer,
    StaffTaskCommentSerializer,
    StaffTaskSerializer,
)


class CrmPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsCrmAdminManagerOrStaffReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.role in {'admin', 'manager'}:
            return True

        if user.role == 'staff':
            return request.method in permissions.SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class BaseCrmViewSet(viewsets.ModelViewSet):
    permission_classes = [IsCrmAdminManagerOrStaffReadOnly]
    pagination_class = CrmPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class CustomerSegmentViewSet(BaseCrmViewSet):
    queryset = CustomerSegment.objects.all()
    serializer_class = CustomerSegmentSerializer
    search_fields = ['code', 'name']
    ordering_fields = ['name', 'code', 'discount_percent']


class CustomerProfileViewSet(BaseCrmViewSet):
    queryset = (
        CustomerProfile.objects.select_related('user', 'segment')
        .prefetch_related('notes__author', 'interactions__created_by')
    )
    serializer_class = CustomerProfileSerializer
    filterset_fields = ['segment']
    search_fields = ['user__full_name', 'user__email', 'user__phone']
    ordering_fields = ['created_at', 'updated_at', 'user__full_name', 'user__email']


class CustomerNoteViewSet(BaseCrmViewSet):
    queryset = CustomerNote.objects.select_related('customer__user', 'author')
    serializer_class = CustomerNoteSerializer
    filterset_fields = ['customer', 'author']
    search_fields = ['customer__user__full_name', 'customer__user__email', 'text', 'author__full_name', 'author__email']
    ordering_fields = ['created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(author=serializer.validated_data.get('author', self.request.user))


class CustomerInteractionViewSet(BaseCrmViewSet):
    queryset = CustomerInteraction.objects.select_related('customer__user', 'created_by')
    serializer_class = CustomerInteractionSerializer
    filterset_fields = ['customer', 'interaction_type', 'created_by']
    search_fields = ['customer__user__full_name', 'customer__user__email', 'description']
    ordering_fields = ['occurred_at', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=serializer.validated_data.get('created_by', self.request.user))


class StaffTaskViewSet(BaseCrmViewSet):
    queryset = (
        StaffTask.objects.select_related('assigned_to', 'related_booking')
        .prefetch_related('checklist_items', 'comments__author')
    )
    serializer_class = StaffTaskSerializer
    filterset_fields = ['status', 'assigned_to', 'related_booking']
    search_fields = ['title']
    ordering_fields = ['created_at', 'updated_at', 'due_at', 'status']


class TaskChecklistItemViewSet(BaseCrmViewSet):
    queryset = TaskChecklistItem.objects.select_related('task')
    serializer_class = StaffTaskChecklistItemSerializer
    filterset_fields = ['task', 'is_completed']
    search_fields = ['title', 'task__title']
    ordering_fields = ['sort_order', 'created_at', 'updated_at']


class TaskCommentViewSet(BaseCrmViewSet):
    queryset = TaskComment.objects.select_related('task', 'author')
    serializer_class = StaffTaskCommentSerializer
    filterset_fields = ['task', 'author']
    search_fields = ['text', 'task__title', 'author__full_name', 'author__email']
    ordering_fields = ['created_at', 'updated_at']

    def perform_create(self, serializer):
        serializer.save(author=serializer.validated_data.get('author', self.request.user))
