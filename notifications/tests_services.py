from django.test import TestCase, override_settings
from django.core import mail
from django.utils import timezone
from users.models import User
from .models import Notification, NotificationType, NotificationPreference, NotificationDelivery
from .services import NotificationService

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NotificationServiceTests(TestCase):
    def setUp(self):
        self.recipient = User.objects.create_user(username='recipient', email='recipient@example.com', password='test')
        self.actor = User.objects.create_user(username='actor', email='actor@example.com', password='test')
        self.notif_type, _ = NotificationType.objects.get_or_create(name='Test Event')

    def test_send_in_app_notification(self):
        NotificationPreference.objects.create(user=self.recipient, notification_type=self.notif_type, via_in_app=True, via_email=False)
        notif = NotificationService.send_notification(
            event_type='Test Event',
            recipient=self.recipient,
            message='Test in-app notification',
            actor=self.actor,
            url='http://example.com/test',
            delivery_channels=['in_app']
        )
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(NotificationDelivery.objects.filter(method='in_app').count(), 1)
        delivery = NotificationDelivery.objects.get(method='in_app')
        self.assertEqual(delivery.status, 'sent')
        self.assertEqual(delivery.notification, notif)

    def test_send_email_notification(self):
        NotificationPreference.objects.create(user=self.recipient, notification_type=self.notif_type, via_in_app=False, via_email=True)
        notif = NotificationService.send_notification(
            event_type='Test Event',
            recipient=self.recipient,
            message='Test email notification',
            actor=self.actor,
            url='http://example.com/test',
            delivery_channels=['email']
        )
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(NotificationDelivery.objects.filter(method='email').count(), 1)
        delivery = NotificationDelivery.objects.get(method='email')
        self.assertEqual(delivery.status, 'sent')
        self.assertEqual(delivery.notification, notif)
        # Check email outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Test email notification', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, [self.recipient.email])

    def test_respects_user_preferences(self):
        NotificationPreference.objects.create(user=self.recipient, notification_type=self.notif_type, via_in_app=False, via_email=True)
        notif = NotificationService.send_notification(
            event_type='Test Event',
            recipient=self.recipient,
            message='Preference-respecting notification',
            actor=self.actor,
            url='http://example.com/test'
        )
        self.assertEqual(NotificationDelivery.objects.filter(method='in_app').count(), 0)
        self.assertEqual(NotificationDelivery.objects.filter(method='email').count(), 1)

    def test_multiple_channels(self):
        NotificationPreference.objects.create(user=self.recipient, notification_type=self.notif_type, via_in_app=True, via_email=True)
        notif = NotificationService.send_notification(
            event_type='Test Event',
            recipient=self.recipient,
            message='Multi-channel notification',
            actor=self.actor,
            url='http://example.com/test',
            delivery_channels=['in_app', 'email']
        )
        self.assertEqual(NotificationDelivery.objects.filter(method='in_app').count(), 1)
        self.assertEqual(NotificationDelivery.objects.filter(method='email').count(), 1)

    def test_creates_notification_type_if_missing(self):
        notif = NotificationService.send_notification(
            event_type='New Event Type',
            recipient=self.recipient,
            message='Should auto-create type',
            actor=self.actor
        )
        self.assertTrue(NotificationType.objects.filter(name='New Event Type').exists())
        self.assertEqual(notif.type.name, 'New Event Type')
