from rest_framework import serializers

from users.models import User

from .models import ExternalContactLink, SupportMessage, SupportTicket
from .permissions import is_support_team
from .services import SupportTicketService


class SupportUserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "phone", "role")
        read_only_fields = fields


class SupportTicketSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ("id", "subject", "status", "channel", "created_at", "closed_at")
        read_only_fields = fields


class SupportMessageSerializer(serializers.ModelSerializer):
    ticket = SupportTicketSummarySerializer(read_only=True)
    ticket_id = serializers.PrimaryKeyRelatedField(
        source="ticket",
        queryset=SupportTicket.objects.select_related("user"),
        write_only=True,
    )
    sender = SupportUserSummarySerializer(read_only=True)
    sender_id = serializers.PrimaryKeyRelatedField(
        source="sender",
        queryset=User.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SupportMessage
        fields = (
            "id",
            "ticket",
            "ticket_id",
            "sender",
            "sender_id",
            "message",
            "attachment",
            "created_at",
        )
        read_only_fields = ("id", "ticket", "sender", "created_at")

    def validate(self, attrs):
        request = self.context["request"]
        ticket = attrs.get("ticket") or getattr(self.instance, "ticket", None)
        sender = attrs.get("sender") or getattr(self.instance, "sender", request.user)

        if ticket and not is_support_team(request.user) and ticket.user_id != request.user.id:
            raise serializers.ValidationError({"ticket_id": "You can only post messages to your own tickets."})

        if sender and not is_support_team(request.user) and sender.id != request.user.id:
            raise serializers.ValidationError({"sender_id": "Only support team can choose a different sender."})

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        sender = validated_data.pop("sender", request.user)
        return SupportTicketService.create_message(sender=sender, **validated_data)


class SupportMessageNestedSerializer(serializers.ModelSerializer):
    sender = SupportUserSummarySerializer(read_only=True)

    class Meta:
        model = SupportMessage
        fields = ("id", "sender", "message", "attachment", "created_at")
        read_only_fields = fields


class SupportTicketSerializer(serializers.ModelSerializer):
    user = SupportUserSummarySerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.all(),
        write_only=True,
        required=False,
    )
    messages = SupportMessageNestedSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "user",
            "user_id",
            "subject",
            "status",
            "channel",
            "created_at",
            "closed_at",
            "messages",
        )
        read_only_fields = ("id", "user", "created_at", "closed_at", "messages")

    def validate(self, attrs):
        request = self.context["request"]
        status = attrs.get("status", getattr(self.instance, "status", "open"))
        user = attrs.get("user", getattr(self.instance, "user", request.user))

        if not is_support_team(request.user):
            if user.id != request.user.id:
                raise serializers.ValidationError({"user_id": "You can only create or update your own tickets."})
            if self.instance is None and status != "open":
                raise serializers.ValidationError({"status": "New tickets must start in open status."})
            if self.instance is not None and "status" in attrs and attrs["status"] != self.instance.status:
                raise serializers.ValidationError({"status": "Only support team can change ticket status."})

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = validated_data.pop("user", request.user)
        return SupportTicketService.create_ticket(user=user, **validated_data)

    def update(self, instance, validated_data):
        return SupportTicketService.update_ticket(instance, **validated_data)


class ExternalContactLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalContactLink
        fields = ("id", "code", "title", "url", "phone", "is_active", "sort_order")
