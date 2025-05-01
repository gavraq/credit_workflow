from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import Notification, NotificationType, NotificationPreference, NotificationDelivery
from users.models import User
from django.utils import timezone
from abc import ABC, abstractmethod

class BaseNotificationDeliveryStrategy(ABC):
    @abstractmethod
    def send(self, notification: Notification, recipient: User, context: dict = None):
        pass

class EmailNotificationStrategy(BaseNotificationDeliveryStrategy):
    def send(self, notification: Notification, recipient: User, context: dict = None):
        # Render email content
        subject = f"Notification: {notification.type.name}"
        message = notification.message
        html_message = None
        if context and 'template' in context:
            html_message = render_to_string(context['template'], context)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient.email],
            html_message=html_message
        )
        NotificationDelivery.objects.create(
            notification=notification,
            method='email',
            delivered_at=timezone.now(),
            status='sent'
        )

class InAppNotificationStrategy(BaseNotificationDeliveryStrategy):
    def send(self, notification: Notification, recipient: User, context: dict = None):
        # In-app notification is already created in DB; just mark delivery
        NotificationDelivery.objects.create(
            notification=notification,
            method='in_app',
            delivered_at=timezone.now(),
            status='sent'
        )

class NotificationService:
    DELIVERY_STRATEGIES = {
        'email': EmailNotificationStrategy(),
        'in_app': InAppNotificationStrategy(),
    }

    @classmethod
    def send_notification(cls, event_type: str, recipient: User, message: str, actor: User = None, url: str = None, context: dict = None, delivery_channels=None):
        notif_type, _ = NotificationType.objects.get_or_create(name=event_type)
        notification = Notification.objects.create(
            type=notif_type,
            recipient=recipient,
            actor=actor,
            message=message,
            url=url
        )
        # Determine channels: user preference or override
        if delivery_channels is None:
            pref = NotificationPreference.objects.filter(user=recipient, notification_type=notif_type).first()
            delivery_channels = []
            if not pref or pref.via_in_app:
                delivery_channels.append('in_app')
            if not pref or pref.via_email:
                delivery_channels.append('email')
        for channel in delivery_channels:
            strategy = cls.DELIVERY_STRATEGIES.get(channel)
            if strategy:
                strategy.send(notification, recipient, context)
        return notification

# Future: TeamsNotificationStrategy (for Microsoft Teams integration)
# class TeamsNotificationStrategy(BaseNotificationDeliveryStrategy):
#     def send(self, notification: Notification, recipient: User, context: dict = None):
#         # Implement Microsoft Teams delivery via webhook/API
#         pass
