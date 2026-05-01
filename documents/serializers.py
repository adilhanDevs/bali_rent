import os

from rest_framework import serializers

from .models import DocumentVerification, UserDocument


class DocumentVerificationSerializer(serializers.ModelSerializer):
    verified_by_email = serializers.EmailField(source='verified_by.email', read_only=True)

    class Meta:
        model = DocumentVerification
        fields = ['id', 'document', 'verified_by', 'verified_by_email', 'status', 'created_at']
        read_only_fields = ['document', 'verified_by', 'created_at']


class UserDocumentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    latest_verification = serializers.SerializerMethodField()
    type = serializers.CharField(write_only=True, required=False)
    document_type = serializers.ChoiceField(choices=UserDocument.DOCUMENT_TYPE_CHOICES, required=False)

    class Meta:
        model = UserDocument
        fields = [
            'id',
            'user',
            'user_email',
            'type',
            'document_type',
            'file',
            'status',
            'rejection_reason',
            'reviewed_by',
            'reviewed_at',
            'created_at',
            'updated_at',
            'latest_verification',
        ]
        read_only_fields = [
            'user',
            'status',
            'rejection_reason',
            'reviewed_by',
            'reviewed_at',
            'created_at',
            'updated_at',
            'latest_verification',
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        document_type = attrs.pop('type', None)
        if document_type and 'document_type' not in attrs:
            attrs['document_type'] = document_type
        if 'document_type' not in attrs:
            raise serializers.ValidationError({'document_type': 'This field is required.'})
        return attrs

    def validate_file(self, value):
        valid_extensions = {'.jpg', '.jpeg', '.png', '.pdf'}
        valid_content_types = {'image/jpeg', 'image/png', 'application/pdf'}
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError('Unsupported file type. Use JPG, PNG or PDF.')
        content_type = getattr(value, 'content_type', '')
        if content_type and content_type not in valid_content_types:
            raise serializers.ValidationError('Unsupported MIME type. Use JPG, PNG or PDF.')
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('File size too large. Max 5MB.')
        return value

    def get_latest_verification(self, obj):
        verification = obj.verifications.first()
        if not verification:
            return None
        return DocumentVerificationSerializer(verification).data


class UserDocumentAdminSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)
    verifications = DocumentVerificationSerializer(many=True, read_only=True)

    class Meta:
        model = UserDocument
        fields = '__all__'
        read_only_fields = [
            'user',
            'document_type',
            'file',
            'created_at',
            'updated_at',
            'reviewed_by',
            'reviewed_at',
            'verifications',
        ]


class DocumentReviewSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
