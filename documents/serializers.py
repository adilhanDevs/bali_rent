from rest_framework import serializers
from .models import UserDocument

class UserDocumentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserDocument
        fields = [
            'id', 'user', 'user_email', 'document_type', 'file', 'status', 
            'rejection_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'status', 'rejection_reason', 'created_at', 'updated_at']

    def validate_file(self, value):
        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
        import os
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError("Unsupported file type. Use JPG, PNG or PDF.")
        
        # Validate max size (5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size too large. Max 5MB.")
            
        return value

class UserDocumentAdminSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)

    class Meta:
        model = UserDocument
        fields = '__all__'
        read_only_fields = ['user', 'document_type', 'file', 'created_at', 'updated_at', 'reviewed_by', 'reviewed_at']

class DocumentReviewSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
