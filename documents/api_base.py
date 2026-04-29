from rest_framework import permissions, viewsets

from bali_rent.permissions import IsOwnerOrAdmin

from .models import UserDocument
from .serializers import UserDocumentSerializer


class UserDocumentViewSet(viewsets.ModelViewSet):
    queryset = UserDocument.objects.all()
    serializer_class = UserDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return UserDocument.objects.all()
        return UserDocument.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=UserDocument.STATUS_PENDING, rejection_reason='')
