from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from bookings.models import Booking
from payments.models import Payment

from .services import NotificationService


@receiver(pre_save, sender=Booking)
def capture_previous_booking_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    instance._previous_status = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()


@receiver(post_save, sender=Booking)
def send_booking_notifications(sender, instance, created, **kwargs):
    if created:
        NotificationService.notify_booking_created(instance)

    previous_status = getattr(instance, '_previous_status', None)
    if instance.status == 'confirmed' and previous_status != 'confirmed':
        NotificationService.notify_booking_confirmed(instance)


@receiver(pre_save, sender=Payment)
def capture_previous_payment_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    instance._previous_status = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()


@receiver(post_save, sender=Payment)
def send_payment_notifications(sender, instance, created, **kwargs):
    if instance.status != 'succeeded':
        return

    previous_status = getattr(instance, '_previous_status', None)
    if created or previous_status != 'succeeded':
        NotificationService.notify_payment_success(instance)
