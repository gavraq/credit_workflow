from django.db import models
from django.conf import settings

class WorkflowState(models.Model):
    """
    Represents a state in the credit workflow (e.g., DRAFT, SUBMITTED, etc.).
    Supports parent-child relationships for draft states.
    """
    state_id = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    is_initial = models.BooleanField(default=False)
    is_final = models.BooleanField(default=False)
    is_draft_state = models.BooleanField(default=False)
    parent_state = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_states')

    def __str__(self):
        return f"{self.name} ({self.state_id})"

class WorkflowStateTransition(models.Model):
    """
    Represents an allowed transition between workflow states.
    """
    transition_id = models.CharField(max_length=12, unique=True)
    from_state = models.ForeignKey(WorkflowState, related_name='outgoing_transitions', on_delete=models.CASCADE)
    to_state = models.ForeignKey(WorkflowState, related_name='incoming_transitions', on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    required_roles = models.CharField(max_length=128, help_text="Comma-separated list of required role IDs (see PRD)")
    actions_required = models.TextField(blank=True)
    is_draft_action = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name}: {self.from_state} → {self.to_state}"

    def is_allowed_for_user(self, user):
        """Check if the transition is allowed for a given user based on role."""
        user_role = getattr(user, 'role', None)
        if not user_role:
            return False
        allowed_roles = [r.strip() for r in self.required_roles.split(',')]
        return user_role in allowed_roles

# Stub for workflow history/audit trail (to be implemented)
# class WorkflowHistory(models.Model):
#     pass
