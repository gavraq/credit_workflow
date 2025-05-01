from django.contrib import admin
from .models import WorkflowState, WorkflowStateTransition

@admin.register(WorkflowState)
class WorkflowStateAdmin(admin.ModelAdmin):
    list_display = ("state_id", "name", "is_initial", "is_final", "is_draft_state", "parent_state")
    search_fields = ("state_id", "name")
    list_filter = ("is_initial", "is_final", "is_draft_state")

@admin.register(WorkflowStateTransition)
class WorkflowStateTransitionAdmin(admin.ModelAdmin):
    list_display = ("transition_id", "name", "from_state", "to_state", "required_roles", "is_draft_action")
    search_fields = ("transition_id", "name")
    list_filter = ("is_draft_action",)
