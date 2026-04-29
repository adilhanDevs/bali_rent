from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from users.models import User

from .models import ChatAttachment, ChatMessage, ChatParticipant, ChatThread, QuickReply


class ChatUserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone', 'role')
        read_only_fields = fields


class ChatParticipantSerializer(serializers.ModelSerializer):
    thread_id = serializers.PrimaryKeyRelatedField(source='thread', queryset=ChatThread.objects.all(), write_only=True)
    user = ChatUserSummarySerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', queryset=User.objects.all(), write_only=True)

    class Meta:
        model = ChatParticipant
        fields = ('id', 'thread_id', 'user', 'user_id', 'role', 'joined_at')
        read_only_fields = ('id', 'user', 'joined_at')

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)


class ChatAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = ChatUserSummarySerializer(read_only=True)
    uploaded_by_id = serializers.PrimaryKeyRelatedField(
        source='uploaded_by',
        queryset=User.objects.all(),
        write_only=True,
        required=False,
    )
    message_id = serializers.PrimaryKeyRelatedField(source='message', queryset=ChatMessage.objects.all(), write_only=True)

    class Meta:
        model = ChatAttachment
        fields = ('id', 'message_id', 'uploaded_by', 'uploaded_by_id', 'file', 'original_name', 'created_at')
        read_only_fields = ('id', 'uploaded_by', 'created_at')

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)


class ChatAttachmentNestedSerializer(serializers.ModelSerializer):
    uploaded_by = ChatUserSummarySerializer(read_only=True)

    class Meta:
        model = ChatAttachment
        fields = ('id', 'uploaded_by', 'file', 'original_name', 'created_at')
        read_only_fields = fields


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = ChatUserSummarySerializer(read_only=True)
    sender_id = serializers.PrimaryKeyRelatedField(source='sender', queryset=User.objects.all(), write_only=True, required=False)
    thread_id = serializers.PrimaryKeyRelatedField(source='thread', queryset=ChatThread.objects.all(), write_only=True)
    attachments = ChatAttachmentNestedSerializer(many=True, read_only=True)

    class Meta:
        model = ChatMessage
        fields = ('id', 'thread_id', 'sender', 'sender_id', 'text', 'created_at', 'updated_at', 'attachments')
        read_only_fields = ('id', 'sender', 'created_at', 'updated_at', 'attachments')

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)


class ChatMessageNestedSerializer(serializers.ModelSerializer):
    sender = ChatUserSummarySerializer(read_only=True)
    attachments = ChatAttachmentNestedSerializer(many=True, read_only=True)

    class Meta:
        model = ChatMessage
        fields = ('id', 'sender', 'text', 'created_at', 'updated_at', 'attachments')
        read_only_fields = fields


class ChatThreadLastMessageSerializer(serializers.Serializer):
    text = serializers.CharField()
    created_at = serializers.DateTimeField()
    sender_name = serializers.CharField(allow_blank=True, allow_null=True)


class ChatThreadListSerializer(serializers.ModelSerializer):
    created_by = ChatUserSummarySerializer(read_only=True)
    participants = ChatParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChatThread
        fields = (
            'id',
            'title',
            'status',
            'created_by',
            'created_at',
            'updated_at',
            'participants',
            'last_message',
            'message_count',
        )
        read_only_fields = fields

    def get_last_message(self, obj):
        text = getattr(obj, 'last_message_text', None)
        created_at = getattr(obj, 'last_message_created_at', None)
        if not text or not created_at:
            return None

        payload = {
            'text': text,
            'created_at': created_at,
            'sender_name': getattr(obj, 'last_message_sender_name', None),
        }
        return ChatThreadLastMessageSerializer(payload).data


class ChatThreadSerializer(serializers.ModelSerializer):
    created_by = ChatUserSummarySerializer(read_only=True)
    participants = ChatParticipantSerializer(many=True, read_only=True)
    participant_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True,
        many=True,
        required=False,
    )
    messages = ChatMessageNestedSerializer(many=True, read_only=True)

    class Meta:
        model = ChatThread
        fields = (
            'id',
            'title',
            'status',
            'created_by',
            'created_at',
            'updated_at',
            'participants',
            'participant_ids',
            'messages',
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at', 'participants', 'messages')

    def validate_participant_ids(self, value):
        if not value:
            raise serializers.ValidationError('At least one participant is required.')
        unique_ids = {user.pk for user in value}
        if len(unique_ids) != len(value):
            raise serializers.ValidationError('Duplicate participants are not allowed.')
        return value

    def _resolve_role(self, user):
        if user.role == 'manager':
            return ChatParticipant.ROLE_MANAGER
        if user.role in {'admin', 'staff'}:
            return ChatParticipant.ROLE_STAFF
        return ChatParticipant.ROLE_CLIENT

    def create(self, validated_data):
        participants = validated_data.pop('participant_ids', [])
        request_user = self.context['request'].user
        thread = ChatThread.objects.create(created_by=request_user, **validated_data)

        all_participants = {request_user.pk: request_user}
        for user in participants:
            all_participants[user.pk] = user

        ChatParticipant.objects.bulk_create(
            [
                ChatParticipant(
                    thread=thread,
                    user=user,
                    role=self._resolve_role(user),
                )
                for user in all_participants.values()
            ]
        )
        return thread

    def update(self, instance, validated_data):
        participants = validated_data.pop('participant_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if participants is not None:
            request_user = self.context['request'].user
            all_participants = {request_user.pk: request_user}
            for user in participants:
                all_participants[user.pk] = user
            instance.participants.exclude(user_id__in=all_participants.keys()).delete()
            existing_ids = set(instance.participants.values_list('user_id', flat=True))
            ChatParticipant.objects.bulk_create(
                [
                    ChatParticipant(thread=instance, user=user, role=self._resolve_role(user))
                    for user_id, user in all_participants.items()
                    if user_id not in existing_ids
                ]
            )
        return instance


class QuickReplySerializer(serializers.ModelSerializer):
    created_by = ChatUserSummarySerializer(read_only=True)

    class Meta:
        model = QuickReply
        fields = ('id', 'title', 'text', 'is_active', 'created_by', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')
