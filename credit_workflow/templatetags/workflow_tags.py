from django import template
from django.utils.html import format_html
from workflow.services import WorkflowEngine
from workflow.models import WorkflowStateTransition
from credit_workflow.models import Notification
import json
from decimal import Decimal

register = template.Library()

@register.simple_tag
def workflow_state_badge(state):
    """Render a workflow state as a colored badge."""
    color_map = {
        # Initial states
        'DRAFT': 'secondary',
        'SUBMITTED': 'info',
        
        # Review states
        'CREDIT_REVIEW': 'primary',
        'BUSINESS_SPONSORSHIP_PENDING': 'primary',
        
        # Processing states
        'BUSINESS_SPONSOR_APPROVED': 'info',
        'CREDIT_ANALYSIS_IN_PROGRESS': 'primary',
        'CREDIT_ANALYSIS_DRAFT': 'secondary',
        'LEGAL_REVIEW_IN_PROGRESS': 'primary',
        'LEGAL_REVIEW_DRAFT': 'secondary',
        'QUESTIONNAIRE_PENDING': 'primary',
        'QUESTIONNAIRE_DRAFT': 'secondary',
        'CREDIT_PAPER_COMPILATION': 'primary',
        
        # Approval states
        'APPROVAL_PENDING_INDIVIDUAL': 'warning',
        'APPROVAL_PENDING_COMMITTEE': 'warning',
        'RETURNED_TO_CREDIT_ANALYSIS': 'warning',
        
        # Final states
        'APPROVED': 'success',
        'REJECTED': 'danger',
        'CANCELLED': 'dark',
    }
    
    color = color_map.get(state.name, 'secondary')
    badge_class = f"badge bg-{color}"
    
    if state.is_draft_state:
        badge_text = f"{state.name} (DRAFT)"
    else:
        badge_text = state.name
        
    return format_html('<span class="{}">{}</span>', badge_class, badge_text)

@register.filter
def is_draft_state(state):
    """Check if a state is a draft state."""
    return state.is_draft_state

@register.simple_tag
def get_available_transitions(credit_request, user):
    """Get transitions available to the user for this credit request."""
    return WorkflowEngine.get_available_transitions(credit_request, user)

@register.filter
def is_final_state(state):
    """Check if a state is a final state."""
    return state.is_final_state

@register.simple_tag
def transition_button(credit_request, transition, user):
    """Render a button for a specific transition."""
    # Check if the transition is allowed for this user
    if transition.is_allowed_for_user(user):
        button_text = transition.name
        
        if transition.is_draft_action:
            btn_class = "btn btn-outline-secondary"
            icon = "save"
        elif "Reject" in transition.name:
            btn_class = "btn btn-outline-danger"
            icon = "x-circle"
        elif "Approve" in transition.name:
            btn_class = "btn btn-success"
            icon = "check-circle"
        elif "Return" in transition.name:
            btn_class = "btn btn-outline-warning"
            icon = "arrow-return-left"
        else:
            btn_class = "btn btn-primary"
            icon = "arrow-right-circle"
            
        return format_html(
            '<button type="submit" class="{}" name="transition" value="{}">'
            '<i class="bi bi-{}"></i> {}</button>',
            btn_class, transition.id, icon, button_text
        )
    return ""

# New notification template tags
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

# Custom JSON encoder for handling Decimal values
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

@register.filter
def to_json(value):
    """Convert a Python object to JSON string."""
    return json.dumps(value, cls=DecimalEncoder)
