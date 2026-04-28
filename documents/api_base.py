from rest_framework import serializers, viewsets, permissions
from .models import UserDocument
from bali_rent.permissions import IsOwnerOrAdmin

class UserDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDocument
        fields = '__all__'
        read_only_fields = ('user', 'status', 'verified_by', 'verified_at')

class UserDocumentViewSet(viewsets.ModelViewSet):
    queryset = UserDocument.objects.all()
    serializer_class = UserDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return UserDocument.objects.all()
        return UserDocument.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
