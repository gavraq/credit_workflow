from django.contrib import admin
from .models import NotificationType, Notification, NotificationPreference, NotificationDelivery

@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("type", "recipient", "actor", "created_at", "read")
    search_fields = ("recipient__username", "actor__username", "message")
    list_filter = ("type", "read", "created_at")
    readonly_fields = ("created_at",)

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "enabled", "via_email", "via_in_app")
    search_fields = ("user__username", "notification_type__name")
    list_filter = ("enabled", "via_email", "via_in_app")

@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("notification", "method", "delivered_at", "status")
    search_fields = ("notification__recipient__username", "method")
    list_filter = ("method", "status", "delivered_at")
