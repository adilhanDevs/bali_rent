from rest_framework import serializers

from bookings.models import Booking
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from users.models import User

from .models import (
    CustomerInteraction,
    CustomerNote,
    CustomerProfile,
    CustomerSegment,
    StaffTask,
    TaskChecklistItem,
    TaskComment,
)


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone', 'role')
        read_only_fields = fields


class CustomerSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerSegment
        fields = ('id', 'code', 'name', 'discount_percent')


class CustomerNoteSerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        source='author',
        queryset=User.objects.all(),
        write_only=True,
        required=False,
    )
    customer_id = serializers.PrimaryKeyRelatedField(
        source='customer',
        queryset=CustomerProfile.objects.select_related('user'),
        write_only=True,
    )

    class Meta:
        model = CustomerNote
        fields = ('id', 'customer_id', 'author', 'author_id', 'text', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at', 'author')


class CustomerInteractionSerializer(serializers.ModelSerializer):
    created_by = UserSummarySerializer(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(
        source='created_by',
        queryset=User.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    customer_id = serializers.PrimaryKeyRelatedField(
        source='customer',
        queryset=CustomerProfile.objects.select_related('user'),
        write_only=True,
    )

    class Meta:
        model = CustomerInteraction
        fields = (
            'id',
            'customer_id',
            'interaction_type',
            'description',
            'occurred_at',
            'created_by',
            'created_by_id',
            'created_at',
        )
        read_only_fields = ('id', 'created_at', 'created_by')


class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=User.objects.all(),
        write_only=True,
    )
    segment = CustomerSegmentSerializer(read_only=True)
    segment_id = serializers.PrimaryKeyRelatedField(
        source='segment',
        queryset=CustomerSegment.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    notes = CustomerNoteSerializer(many=True, read_only=True)
    interactions = CustomerInteractionSerializer(many=True, read_only=True)

    class Meta:
        model = CustomerProfile
        fields = (
            'id',
            'user',
            'user_id',
            'segment',
            'segment_id',
            'created_at',
            'updated_at',
            'notes',
            'interactions',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'user', 'segment', 'notes', 'interactions')


class StaffTaskChecklistItemSerializer(serializers.ModelSerializer):
    task_id = serializers.PrimaryKeyRelatedField(source='task', queryset=StaffTask.objects.all(), write_only=True)

    class Meta:
        model = TaskChecklistItem
        fields = ('id', 'task_id', 'title', 'is_completed', 'sort_order', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)


class StaffTaskCommentSerializer(serializers.ModelSerializer):
    task_id = serializers.PrimaryKeyRelatedField(source='task', queryset=StaffTask.objects.all(), write_only=True)
    author = UserSummarySerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        source='author',
        queryset=User.objects.all(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = TaskComment
        fields = ('id', 'task_id', 'author', 'author_id', 'text', 'created_at', 'updated_at')
        read_only_fields = ('id', 'author', 'created_at', 'updated_at')

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)


class StaffTaskSerializer(serializers.ModelSerializer):
    assigned_to = UserSummarySerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        source='assigned_to',
        queryset=User.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    related_booking_id = serializers.PrimaryKeyRelatedField(
        source='related_booking',
        queryset=Booking.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    checklist_items = StaffTaskChecklistItemSerializer(many=True, read_only=True)
    comments = StaffTaskCommentSerializer(many=True, read_only=True)

    class Meta:
        model = StaffTask
        fields = (
            'id',
            'title',
            'description',
            'assigned_to',
            'assigned_to_id',
            'related_booking_id',
            'status',
            'due_at',
            'created_at',
            'updated_at',
            'checklist_items',
            'comments',
        )
        read_only_fields = ('id', 'assigned_to', 'created_at', 'updated_at', 'checklist_items', 'comments')

    def validate(self, attrs):
        instance = self.instance
        due_at = attrs.get('due_at', getattr(instance, 'due_at', None))
        status = attrs.get('status', getattr(instance, 'status', 'pending'))

        if due_at and due_at < timezone.now():
            raise serializers.ValidationError({'due_at': 'Due date cannot be in the past.'})

        allowed_transitions = {
            'pending': {'pending', 'in_progress', 'cancelled'},
            'in_progress': {'in_progress', 'completed', 'cancelled'},
            'completed': {'completed'},
            'cancelled': {'cancelled'},
        }

        if instance is None:
            if status != 'pending':
                raise serializers.ValidationError({'status': 'New tasks must start in pending status.'})
        else:
            previous_status = instance.status
            if status not in allowed_transitions.get(previous_status, {previous_status}):
                raise serializers.ValidationError({'status': f'Cannot transition task from {previous_status} to {status}.'})
            if status == 'completed' and instance.checklist_items.filter(is_completed=False).exists():
                raise serializers.ValidationError({'status': 'All checklist items must be completed before finishing the task.'})

        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
