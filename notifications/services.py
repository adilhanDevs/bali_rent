import logging
from django.conf import settings
from .models import Notification, NotificationTemplate
from users.models import UserDevice, User

logger = logging.getLogger(__name__)


DOCUMENT_TYPE_LABELS = {
    'passport': {
        'en': 'passport',
        'ru': 'паспорт',
        'zh': '护照',
        'id': 'paspor',
        'de': 'Reisepass',
        'fr': 'passeport',
    },
    'driver_license': {
        'en': "driver's license",
        'ru': 'водительские права',
        'zh': '驾照',
        'id': 'SIM',
        'de': 'Führerschein',
        'fr': 'permis de conduire',
    },
    'selfie': {
        'en': 'selfie with document',
        'ru': 'селфи с документом',
        'zh': '证件自拍',
        'id': 'selfie dengan dokumen',
        'de': 'Selfie mit Dokument',
        'fr': 'selfie avec document',
    },
}


NOTIFICATION_COPY = {
    'booking_created': {
        'en': ('Booking {number} created', 'Your booking was created. Complete payment to confirm it.'),
        'ru': ('Бронь {number} создана', 'Бронирование создано. Завершите оплату, чтобы подтвердить его.'),
        'zh': ('订单 {number} 已创建', '您的订单已创建。请完成付款以确认订单。'),
        'id': ('Booking {number} dibuat', 'Booking Anda sudah dibuat. Selesaikan pembayaran untuk mengonfirmasi.'),
        'de': ('Buchung {number} erstellt', 'Deine Buchung wurde erstellt. Schließe die Zahlung ab, um sie zu bestätigen.'),
        'fr': ('Réservation {number} créée', 'Votre réservation a été créée. Finalisez le paiement pour la confirmer.'),
    },
    'booking_confirmed': {
        'en': ('Booking {number} confirmed', 'Your booking has been confirmed and is awaiting delivery.'),
        'ru': ('Бронь {number} подтверждена', 'Ваша бронь подтверждена и ожидает доставки.'),
        'zh': ('订单 {number} 已确认', '您的订单已确认，正在等待交付。'),
        'id': ('Booking {number} dikonfirmasi', 'Booking Anda sudah dikonfirmasi dan menunggu pengantaran.'),
        'de': ('Buchung {number} bestätigt', 'Deine Buchung ist bestätigt und wartet auf die Lieferung.'),
        'fr': ('Réservation {number} confirmée', 'Votre réservation est confirmée et en attente de livraison.'),
    },
    'booking_cancelled': {
        'en': ('Booking {number} cancelled', 'Your booking has been cancelled successfully.'),
        'ru': ('Бронь {number} отменена', 'Ваша бронь была успешно отменена.'),
        'zh': ('订单 {number} 已取消', '您的订单已成功取消。'),
        'id': ('Booking {number} dibatalkan', 'Booking Anda berhasil dibatalkan.'),
        'de': ('Buchung {number} storniert', 'Deine Buchung wurde erfolgreich storniert.'),
        'fr': ('Réservation {number} annulée', 'Votre réservation a bien été annulée.'),
    },
    'payment_pending': {
        'en': ('Payment started for {number}', 'Complete your payment to confirm the booking.'),
        'ru': ('Оплата по брони {number} начата', 'Завершите оплату, чтобы подтвердить бронь.'),
        'zh': ('订单 {number} 的付款已发起', '请完成付款以确认订单。'),
        'id': ('Pembayaran untuk {number} dimulai', 'Selesaikan pembayaran untuk mengonfirmasi booking.'),
        'de': ('Zahlung für {number} gestartet', 'Schließe die Zahlung ab, um die Buchung zu bestätigen.'),
        'fr': ('Paiement démarré pour {number}', 'Finalisez le paiement pour confirmer la réservation.'),
    },
    'payment_succeeded': {
        'en': ('Payment received for {number}', 'Your payment was processed successfully and your booking is confirmed.'),
        'ru': ('Оплата по брони {number} получена', 'Оплата прошла успешно, и ваша бронь подтверждена.'),
        'zh': ('订单 {number} 的付款已收到', '您的付款已成功处理，订单已确认。'),
        'id': ('Pembayaran untuk {number} diterima', 'Pembayaran berhasil diproses dan booking Anda dikonfirmasi.'),
        'de': ('Zahlung für {number} erhalten', 'Deine Zahlung wurde erfolgreich verarbeitet und die Buchung ist bestätigt.'),
        'fr': ('Paiement reçu pour {number}', 'Votre paiement a été traité avec succès et la réservation est confirmée.'),
    },
    'document_uploaded': {
        'en': ('Document uploaded', 'Your {document} was uploaded and is pending review.'),
        'ru': ('Документ загружен', 'Ваш документ "{document}" загружен и ожидает проверки.'),
        'zh': ('证件已上传', '您的{document}已上传，等待审核。'),
        'id': ('Dokumen diunggah', 'Dokumen {document} Anda sudah diunggah dan menunggu peninjauan.'),
        'de': ('Dokument hochgeladen', 'Dein Dokument "{document}" wurde hochgeladen und wartet auf Prüfung.'),
        'fr': ('Document téléversé', 'Votre document "{document}" a été téléversé et attend une vérification.'),
    },
    'document_approved': {
        'en': ('Document approved', 'Your {document} was approved.'),
        'ru': ('Документ подтверждён', 'Ваш документ "{document}" был подтверждён.'),
        'zh': ('证件已通过', '您的{document}已审核通过。'),
        'id': ('Dokumen disetujui', 'Dokumen {document} Anda disetujui.'),
        'de': ('Dokument genehmigt', 'Dein Dokument "{document}" wurde genehmigt.'),
        'fr': ('Document approuvé', 'Votre document "{document}" a été approuvé.'),
    },
    'document_rejected': {
        'en': ('Document rejected', 'Your {document} was rejected. {reason}'),
        'ru': ('Документ отклонён', 'Ваш документ "{document}" был отклонён. {reason}'),
        'zh': ('证件被拒绝', '您的{document}被拒绝。{reason}'),
        'id': ('Dokumen ditolak', 'Dokumen {document} Anda ditolak. {reason}'),
        'de': ('Dokument abgelehnt', 'Dein Dokument "{document}" wurde abgelehnt. {reason}'),
        'fr': ('Document refusé', 'Votre document "{document}" a été refusé. {reason}'),
    },
}


class NotificationService:
    @staticmethod
    def _preferred_language(user):
        profile = getattr(user, 'profile', None)
        language = getattr(profile, 'preferred_language', 'en') or 'en'
        return str(language).strip().lower().split('-')[0]

    @staticmethod
    def _document_label(document_type, language):
        labels = DOCUMENT_TYPE_LABELS.get(document_type or '', {})
        return labels.get(language) or labels.get('en') or document_type or 'document'

    @staticmethod
    def _resolve_context(notification_type, data_json):
        data = data_json or {}
        context = {
            'number': data.get('booking_number') or '',
            'document': 'document',
            'reason': data.get('rejection_reason') or '',
        }

        booking_id = data.get('booking_id')
        if booking_id:
            try:
                from bookings.models import Booking
                booking = Booking.objects.only('public_number').get(id=booking_id)
                context['number'] = booking.public_number
            except Exception:
                pass

        document_id = data.get('document_id')
        if document_id:
            try:
                from documents.models import UserDocument
                document = UserDocument.objects.only('document_type').get(id=document_id)
                context['document_type'] = document.document_type
                context['reason'] = context['reason'] or data.get('rejection_reason') or ''
            except Exception:
                pass

        return context

    @staticmethod
    def _localize(user, notification_type, title, body, data_json):
        language = NotificationService._preferred_language(user)
        variants = NOTIFICATION_COPY.get(notification_type)
        if not variants:
            return title, body

        template = variants.get(language) or variants.get('en')
        if not template:
            return title, body

        context = NotificationService._resolve_context(notification_type, data_json)
        context['document'] = NotificationService._document_label(context.get('document_type'), language)
        context['reason'] = context.get('reason', '').strip()
        if context['reason']:
            if language == 'zh':
                context['reason'] = f"原因：{context['reason']}"
            elif language == 'ru':
                context['reason'] = f"Причина: {context['reason']}"
            elif language == 'id':
                context['reason'] = f"Alasan: {context['reason']}"
            elif language == 'de':
                context['reason'] = f"Grund: {context['reason']}"
            elif language == 'fr':
                context['reason'] = f"Raison : {context['reason']}"
            else:
                context['reason'] = f"Reason: {context['reason']}"

        localized_title = template[0].format(**context).strip()
        localized_body = template[1].format(**context).strip()
        return localized_title, localized_body

    @staticmethod
    def create_notification(user, title, body, notification_type, data_json=None):
        title, body = NotificationService._localize(user, notification_type, title, body, data_json)
        notification = Notification.objects.create(
            user=user,
            title=title,
            body=body,
            type=notification_type,
            data_json=data_json
        )
        NotificationService.send_push(user, title, body, data_json)
        return notification

    @staticmethod
    def send_push(user, title, body, data=None):
        devices = UserDevice.objects.filter(user=user, is_active=True)
        if not devices.exists():
            logger.info(f"No active devices for user {user.email}")
            return

        # Safe stub for dev if Firebase not configured
        fcm_api_key = getattr(settings, 'FCM_SERVER_KEY', None)
        
        for device in devices:
            if not fcm_api_key:
                logger.info(f"[STUB] Sending push to {device.fcm_token}: {title} - {body}")
            else:
                # In a real implementation, call FCM API here
                logger.info(f"Sending real push to {device.fcm_token} (FCM implementation pending)")

    @staticmethod
    def send_to_all(title, body, notification_type, data_json=None):
        users = User.objects.filter(is_active=True)
        for user in users:
            NotificationService.create_notification(user, title, body, notification_type, data_json)

    @staticmethod
    def send_to_segment(segment, title, body, notification_type, data_json=None):
        # Example segment logic: role-based
        users = User.objects.filter(role=segment, is_active=True)
        for user in users:
            NotificationService.create_notification(user, title, body, notification_type, data_json)
