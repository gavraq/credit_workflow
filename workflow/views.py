from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.urls import reverse

from .models import WorkflowState, WorkflowStateTransition
from .services import WorkflowEngine
from credit_workflow.models import CreditRequest

@login_required
def transition_request(request, credit_request_id, to_state_id):
    """
    Handle a workflow state transition for a credit request.
    """
    # Only support POST requests
    if request.method != 'POST':
        return redirect('creditrequest_detail', pk=credit_request_id)
        
    # Get objects
    credit_request = get_object_or_404(CreditRequest, id=credit_request_id)
    to_state = get_object_or_404(WorkflowState, id=to_state_id)
    
    # Get action name if provided
    action_name = request.POST.get('action_name')
    
    # Get comments if provided
    comments = request.POST.get('comments')
    
    try:
        # Perform the transition
        WorkflowEngine.transition_request(
            credit_request=credit_request,
            to_state=to_state,
            user=request.user,
            action_name=action_name,
            comments=comments
        )
        
        # Success message based on the target state
        if to_state.is_draft_state:
            messages.success(request, f"Draft saved successfully.")
        elif to_state.is_final_state:
            if to_state.name == "APPROVED":
                messages.success(request, f"Credit request approved successfully.")
            elif to_state.name == "REJECTED":
                messages.success(request, f"Credit request rejected.")
            elif to_state.name == "CANCELLED":
                messages.success(request, f"Credit request cancelled.")
        else:
            messages.success(request, f"Credit request moved to {to_state.name} state.")
            
    except PermissionDenied as e:
        messages.error(request, str(e))
    except ValidationError as e:
        messages.error(request, str(e))
    
    # Redirect back to the credit request detail page
    return redirect('creditrequest_detail', pk=credit_request_id)
