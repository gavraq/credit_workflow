from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from workflow.models import WorkflowState, WorkflowStateTransition
from credit_workflow.models import CreditRequest, Notification
from users.models import User

class WorkflowEngine:
    """
    Service for managing workflow state transitions and enforcing permissions.
    """
    @staticmethod
    @transaction.atomic
    def transition_request(credit_request: CreditRequest, to_state: WorkflowState, user: User, 
                          action_name: str = None, comments: str = None):
        """
        Perform a workflow state transition for a credit request, enforcing permissions and business rules.
        Raises PermissionDenied or ValidationError on failure.
        
        Args:
            credit_request: The CreditRequest object to transition
            to_state: The target WorkflowState
            user: The User performing the transition
            action_name: Optional name of the action (for validation)
            comments: Optional comments about the transition
            
        Returns:
            The updated CreditRequest
        """
        from_state = credit_request.workflow_state
        
        # Find the valid transition
        try:
            transition = WorkflowStateTransition.objects.get(from_state=from_state, to_state=to_state)
        except WorkflowStateTransition.DoesNotExist:
            raise ValidationError(f"No transition from {from_state} to {to_state}.")
            
        # Check user role/permissions
        allowed_roles = [role.strip() for role in transition.required_roles.split(",")]
        if user.role not in allowed_roles:
            raise PermissionDenied(f"User role '{user.role}' cannot perform this transition.")
            
        # Check action name if provided
        if action_name and transition.name != action_name:
            raise ValidationError(f"Transition action '{action_name}' does not match transition '{transition.name}'.")
            
        # Perform transition
        credit_request.workflow_state = to_state
        
        # Handle draft states
        if to_state.is_draft_state:
            # Don't send notifications or track publicly for draft states
            pass
        else:
            # Create history record (future implementation)
            # WorkflowHistory.objects.create(
            #    credit_request=credit_request,
            #    from_state=from_state,
            #    to_state=to_state,
            #    user=user,
            #    comments=comments
            # )
            pass
        
        # Handle state-specific actions
        if to_state.name == "SUBMITTED":
            credit_request.submitted_at = timezone.now()
        elif to_state.name in ["APPROVED", "REJECTED", "CANCELLED"]:
            credit_request.completed_at = timezone.now()
            
        credit_request.save(update_fields=["workflow_state", "submitted_at", "completed_at"])
        
        # Create notifications
        WorkflowEngine._create_transition_notifications(credit_request, from_state, to_state, user)
        
        return credit_request

    @staticmethod
    def get_available_transitions(credit_request: CreditRequest, user: User):
        """
        Return a queryset of WorkflowStateTransition objects available to the user for this credit request.
        """
        transitions = WorkflowStateTransition.objects.filter(from_state=credit_request.workflow_state)
        
        # Filter by user role
        user_role = user.role
        return [t for t in transitions if user_role in [role.strip() for role in t.required_roles.split(",")]]
        
    @staticmethod
    def get_next_state_for_action(credit_request: CreditRequest, action_name: str):
        """
        Get the next state for a given action name from the current state.
        """
        try:
            transition = WorkflowStateTransition.objects.get(
                from_state=credit_request.workflow_state, 
                name=action_name
            )
            return transition.to_state
        except WorkflowStateTransition.DoesNotExist:
            return None
    
    @staticmethod
    def _create_transition_notifications(credit_request, from_state, to_state, actor):
        """Create notifications for relevant users based on state transition."""
        # Don't notify for draft state transitions
        if to_state.is_draft_state or from_state.is_draft_state:
            return
            
        # Determine notification recipients based on the transition
        to_notify = set()
        
        # Always notify the submitter
        to_notify.add(credit_request.submitter)
        
        # Add state-specific notifications
        if to_state.name == "CREDIT_REVIEW":
            # Notify Credit Analysts when a new request needs review
            # In a real implementation, you'd query all users with Credit Analyst role
            if credit_request.assigned_analyst:
                to_notify.add(credit_request.assigned_analyst)
                
        elif to_state.name == "BUSINESS_SPONSORSHIP_PENDING":
            # Notify the Business Sponsor
            to_notify.add(credit_request.business_sponsor)
            if credit_request.second_sponsor:
                to_notify.add(credit_request.second_sponsor)
                
        elif to_state.name == "CREDIT_ANALYSIS_IN_PROGRESS":
            # Notify assigned analyst
            if credit_request.assigned_analyst:
                to_notify.add(credit_request.assigned_analyst)
                
        elif to_state.name == "QUESTIONNAIRE_PENDING":
            # Notify relationship manager (submitter)
            to_notify.add(credit_request.submitter)
            
        elif to_state.name == "LEGAL_REVIEW_IN_PROGRESS":
            # Notify legal reviewers (in a real implementation, query users with Legal Reviewer role)
            pass
            
        elif to_state.name in ["APPROVED", "REJECTED"]:
            # Notify submitter and business sponsor
            to_notify.add(credit_request.submitter)
            to_notify.add(credit_request.business_sponsor)
            
        # Create notifications for all recipients (excluding the actor)
        for recipient in to_notify:
            if recipient != actor:  # Don't notify the person who performed the action
                Notification.objects.create(
                    user=recipient,
                    type="workflow",
                    content=f"Credit request {credit_request.request_number} for {credit_request.counterparty.name} "
                            f"has moved to {to_state.name} state.",
                    link=f"/credit_request/{credit_request.id}/"
                )
