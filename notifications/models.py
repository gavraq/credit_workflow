from django.db import models
from users.models import User

class NotificationType(models.Model):
    """
    Categorizes notifications (e.g., workflow event, document update, comment, etc.)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Notification(models.Model):
    """
    A notification event for a user, related to a workflow or document event.
    """
    type = models.ForeignKey(NotificationType, on_delete=models.PROTECT)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications_sent")
    message = models.TextField()
    url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.type.name} for {self.recipient.username} at {self.created_at}"

class NotificationPreference(models.Model):
    """
    Stores user notification preferences by notification type.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notification_preferences")
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)
    via_email = models.BooleanField(default=True)
    via_in_app = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "notification_type")

    def __str__(self):
        return f"{self.user.username} - {self.notification_type.name}"

class NotificationDelivery(models.Model):
    """
    Tracks the delivery status of a notification (e.g., email, in-app, etc.).
    """
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="deliveries")
    method = models.CharField(max_length=32)  # e.g., 'email', 'in_app'
    delivered_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, default="pending")  # e.g., 'pending', 'sent', 'failed'
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.method} delivery for {self.notification}"
