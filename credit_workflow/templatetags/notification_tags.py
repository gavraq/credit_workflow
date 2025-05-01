from django import template
from credit_workflow.models import Notification

register = template.Library()

@register.simple_tag
def unread_notification_count(user):
    """Return the count of unread notifications for a user."""
    if user.is_authenticated:
        return Notification.objects.filter(user=user, read=False).count()
    return 0

@register.simple_tag
def user_notifications(user, limit=5):
    """Return a limited number of notifications for a user."""
    if user.is_authenticated:
        return Notification.objects.filter(user=user).order_by('-created_at')[:limit]
    return []
