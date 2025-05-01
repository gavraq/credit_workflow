from django.shortcuts import redirect, get_object_or_404
from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone

from workflow.models import WorkflowState
from .models import CreditRequest, Notification

class BusinessSponsorshipView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for handling business sponsorship decisions on credit requests.
    Only business sponsors can approve or reject requests in the BUSINESS_SPONSORSHIP_PENDING state.
    """
    model = CreditRequest
    template_name = 'credit_workflow/business_sponsor_form.html'
    context_object_name = 'object'
    fields = []  # No fields from the model are directly edited in the form
    
    def test_func(self):
        """
        Check if the current user is the business sponsor for this credit request
        or has admin privileges.
        """
        credit_request = self.get_object()
        return (self.request.user == credit_request.business_sponsor or 
                self.request.user.is_staff)
    
    def post(self, request, *args, **kwargs):
        """
        Handle the POST request to approve or reject the credit request as a business sponsor.
        """
        credit_request = self.get_object()
        
        # Check if the request is in the correct state
        if credit_request.workflow_state.name != "BUSINESS_SPONSORSHIP_PENDING":
            messages.error(request, "This credit request is not currently pending business sponsorship.")
            return redirect('creditrequest_detail', pk=credit_request.pk)
        
        # Get form data
        sponsor_decision = request.POST.get('sponsor_decision')
        sponsor_comments = request.POST.get('sponsor_comments', '')
        rejection_reason = request.POST.get('rejection_reason', '')
        
        # Process the decision
        if sponsor_decision == 'approve':
            try:
                # Find the BUSINESS_SPONSOR_APPROVED state
                approved_state = WorkflowState.objects.get(name="BUSINESS_SPONSOR_APPROVED")
                
                # Update the credit request
                credit_request.workflow_state = approved_state
                credit_request.credit_review_notes = f"{credit_request.credit_review_notes or ''}\n\nBusiness Sponsor Approval ({timezone.now().strftime('%Y-%m-%d %H:%M')}): {sponsor_comments}"
                credit_request.save()
                
                # Create notification for relevant users
                if credit_request.assigned_analyst:
                    Notification.objects.create(
                        user=credit_request.assigned_analyst,
                        type="workflow",
                        content=f"Credit request #{credit_request.request_number} has been approved by business sponsor and is ready for credit analysis.",
                        link=f"/credit-request/{credit_request.pk}/"
                    )
                
                messages.success(request, "Credit request has been approved as a business sponsor.")
                
            except WorkflowState.DoesNotExist:
                messages.error(request, "Error: Required workflow state not found.")
                return redirect('creditrequest_detail', pk=credit_request.pk)
                
        elif sponsor_decision == 'reject':
            try:
                # Find the REJECTED state
                rejected_state = WorkflowState.objects.get(name="REJECTED")
                
                # Format rejection reason
                if rejection_reason:
                    formatted_reason = f"Rejection Reason: {rejection_reason}\n"
                else:
                    formatted_reason = ""
                
                # Update the credit request
                credit_request.workflow_state = rejected_state
                credit_request.credit_review_notes = f"{credit_request.credit_review_notes or ''}\n\nBusiness Sponsor Rejection ({timezone.now().strftime('%Y-%m-%d %H:%M')}):\n{formatted_reason}{sponsor_comments}"
                credit_request.save()
                
                # Create notification for submitter
                Notification.objects.create(
                    user=credit_request.submitter,
                    type="workflow",
                    content=f"Credit request #{credit_request.request_number} has been rejected by business sponsor.",
                    link=f"/credit-request/{credit_request.pk}/"
                )
                
                messages.success(request, "Credit request has been rejected as a business sponsor.")
                
            except WorkflowState.DoesNotExist:
                messages.error(request, "Error: Required workflow state not found.")
                return redirect('creditrequest_detail', pk=credit_request.pk)
        else:
            messages.error(request, "Invalid decision. Please select either approve or reject.")
            return self.get(request, *args, **kwargs)
        
        return redirect('creditrequest_detail', pk=credit_request.pk)
