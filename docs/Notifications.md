# Notification System Approach & Implementation

## Overview
The notification system provides users with timely, actionable updates about workflow events, document changes, reminders, and other relevant activities. It supports both in-app notifications and user preferences for notification types.

---

## Models
- **Notification**
  - Fields: `user`, `type` (workflow, document, reminder, other), `content`, `link`, `read`, `dismissed`, `created_at`
  - Tracks individual notifications for each user.
- **NotificationPreference**
  - Fields: `user`, `type`, `enabled`
  - Allows users to enable/disable notifications by type.

---

## Views & Templates
- **NotificationCenterView**: Lists and filters notifications for the logged-in user (`notification_center.html`).
- **NotificationPreferencesView**: Lists and updates user notification preferences (`notification_preferences.html`).
- **NotificationMarkReadView**: Marks a notification as read (POST-only).
- **NotificationDismissView**: Dismisses a notification (POST-only).

---

## API Endpoints (Django REST Framework)
- `GET /api/notifications/`: List current user's notifications.
- `POST /api/notifications/<pk>/mark-read/`: Mark notification as read.
- `POST /api/notifications/<pk>/dismiss/`: Dismiss notification.
  - All endpoints require authentication and only operate on the current user's notifications.

---

## Security & Permissions
- All notification views and API endpoints enforce user authentication and object-level permissions.
- Users can only view, mark, or dismiss their own notifications.

---

## Extensibility
- New notification types can be added via the `NOTIFICATION_TYPES` tuple in the model.
- Real-time updates can be integrated via Django Channels or polling the API endpoints.
- API endpoints are ready for AJAX integration in the frontend.

---

## Example Usage
- **In-app:** Users access the notification center to see unread or recent notifications, mark them as read, or dismiss them.
- **Integration:** Frontend can poll `/api/notifications/` or use websockets for real-time updates.

---

## Testing & Quality
- All major actions (list, mark as read, dismiss, preferences) are covered by dedicated Django and DRF tests.

---

## File Locations
- Models: `credit_workflow/models.py`
- Forms: `credit_workflow/forms.py`
- Views: `credit_workflow/views.py`
- Templates: `credit_workflow/templates/credit_workflow/notification_center.html`, `notification_preferences.html`
- API: `credit_workflow/views.py`, `credit_workflow/serializers.py`, `credit_workflow/urls.py`
