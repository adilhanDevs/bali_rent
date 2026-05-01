from django.db import transaction
from django.utils import timezone

from events.services import emit_event
from .models import SupportMessage, SupportTicket


class SupportTicketService:
    @staticmethod
    @transaction.atomic
    def create_ticket(*, user, subject, channel, status=SupportTicket.STATUS_CHOICES[0][0]):
        ticket = SupportTicket.objects.create(
            user=user,
            subject=subject,
            channel=channel,
            status=status,
        )
        SupportTicketService.sync_closed_at(ticket)
        
        emit_event("ticket_created", {
            "user": user,
            "ticket_id": ticket.id,
            "subject": subject,
            "channel": channel,
        })
        
        return ticket

    @staticmethod
    @transaction.atomic
    def update_ticket(ticket, **changes):
        for field, value in changes.items():
            setattr(ticket, field, value)
        ticket.save()
        SupportTicketService.sync_closed_at(ticket)
        return ticket

    @staticmethod
    def sync_closed_at(ticket):
        if ticket.status == "closed" and ticket.closed_at is None:
            ticket.closed_at = timezone.now()
            ticket.save(update_fields=["closed_at"])
        elif ticket.status != "closed" and ticket.closed_at is not None:
            ticket.closed_at = None
            ticket.save(update_fields=["closed_at"])
        return ticket

    @staticmethod
    @transaction.atomic
    def create_message(*, ticket, sender, message, attachment=None):
        support_message = SupportMessage.objects.create(
            ticket=ticket,
            sender=sender,
            message=message,
            attachment=attachment,
        )

        if ticket.status == "closed":
            ticket.status = "in_progress"
            ticket.closed_at = None
            ticket.save(update_fields=["status", "closed_at"])
        elif sender and sender.id != ticket.user_id and ticket.status == "open":
            ticket.status = "in_progress"
            ticket.save(update_fields=["status"])

        emit_event("message_sent", {
            "user": sender,
            "ticket_id": ticket.id,
            "message_id": support_message.id,
            "text": message,
        })

        return support_message
