"""
Enhanced CreditRequestDetailView implementation.
This file contains only the modified CreditRequestDetailView class,
which will be integrated into the main views.py file.
"""

from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import CreditRequest, CreditQuestionnaire, LegalReview, CreditAnalysis, Document
from workflow.models import WorkflowState

class CreditRequestDetailView(LoginRequiredMixin, DetailView):
    """
    Enhanced detail view for Credit Requests that shows all components based on workflow state
    and includes permission checks for each section.
    """
    model = CreditRequest
    template_name = 'credit_workflow/creditrequest_detail.html'
    context_object_name = 'credit_request'
    
    def get_context_data(self, **kwargs):
        """
        Enhanced context data to include all components of the credit workflow
        and permission checks for each section.
        """
        context = super().get_context_data(**kwargs)
        credit_request = self.object
        user = self.request.user
        
        # Add related components
        try:
            questionnaire = CreditQuestionnaire.objects.get(credit_request=credit_request)
            print(f"DEBUG - Found questionnaire for credit request {credit_request.id}")
            print(f"DEBUG - Questionnaire ID: {questionnaire.id}")
            print(f"DEBUG - Questionnaire content length: {len(questionnaire.content or '')}")
            print(f"DEBUG - Questionnaire content preview: {(questionnaire.content or '')[:100]}...")
            context['questionnaire'] = questionnaire
        except CreditQuestionnaire.DoesNotExist:
            print(f"DEBUG - No questionnaire found for credit request {credit_request.id}")
            context['questionnaire'] = None
            
        try:
            context['legal_review'] = LegalReview.objects.get(credit_request=credit_request)
        except LegalReview.DoesNotExist:
            context['legal_review'] = None
            
        try:
            context['credit_analysis'] = CreditAnalysis.objects.get(credit_request=credit_request)
        except CreditAnalysis.DoesNotExist:
            context['credit_analysis'] = None
            
        # Documents
        context['documents'] = Document.objects.filter(credit_request=credit_request)
        
        # Add workflow progress data
        context['workflow_progress'] = self._get_workflow_progress(credit_request)
        
        # Add permission checks for section editing
        context.update({
            'can_edit_request': self._can_edit_request(user, credit_request),
            'can_edit_review': self._can_edit_review(user, credit_request),
            'can_edit_sponsorship': self._can_edit_sponsorship(user, credit_request),
            'can_edit_questionnaire': self._can_edit_questionnaire(user, credit_request),
            'can_edit_legal': self._can_edit_legal(user, credit_request),
            'can_edit_analysis': self._can_edit_analysis(user, credit_request),
        })
        
        return context
    
    def _get_workflow_progress(self, credit_request):
        """
        Calculate workflow progress data for the progress bar.
        Returns a list of workflow stages with status and dates.
        """
        workflow_states = WorkflowState.objects.all().order_by('id')
        current_state = credit_request.workflow_state
        
        progress = []
        for state in workflow_states:
            # Skip draft states in the progress bar
            if hasattr(state, 'is_draft_state') and state.is_draft_state:
                continue
                
            # Determine the status of this state
            status = 'pending'  # Default status
            
            if state == current_state:
                status = 'current'
            elif self._is_state_completed(state, current_state, workflow_states):
                status = 'completed'
            
            # Get the dates for this state
            started_at = None
            completed_at = None
            
            # Add specific field mapping for key workflow states
            if state.name == 'DRAFT' or state.name == 'SUBMITTED':
                started_at = credit_request.created_at
                completed_at = credit_request.submitted_at if status == 'completed' else None
            elif state.name == 'CREDIT_REVIEW':
                started_at = credit_request.submitted_at
                completed_at = getattr(credit_request, 'credit_review_completed_at', None)
            elif state.name == 'BUSINESS_SPONSORSHIP_PENDING':
                started_at = getattr(credit_request, 'credit_review_completed_at', None) 
                completed_at = getattr(credit_request, 'sponsorship_completed_at', None)
            # Add similar mappings for other states
            
            # Add this state to the progress
            progress.append({
                'id': state.state_id if hasattr(state, 'state_id') else str(state.id),
                'title': state.name.replace('_', ' ').title(),
                'status': status,
                'started_at': started_at,
                'completed_at': completed_at,
            })
            
        return progress
    
    def _is_state_completed(self, state, current_state, workflow_states):
        """
        Determine if a given state is completed based on the current state.
        We consider a state completed if we've moved past it in the workflow.
        """
        # Convert workflow states to a list and find the indices
        state_list = list(workflow_states)
        try:
            current_index = state_list.index(current_state)
            state_index = state_list.index(state)
            
            # If the state comes before the current state, it's completed
            return state_index < current_index
        except ValueError:
            # Handle case where state might not be in the list
            return False
    
    def _can_edit_request(self, user, credit_request):
        """
        Check if the user can edit the credit request.
        Only relationship managers can edit their own requests, and only in DRAFT state.
        """
        # Check if the user is the submitter
        is_submitter = user == credit_request.submitter
        
        # Check if the request is in DRAFT state
        is_draft = credit_request.workflow_state.name == 'DRAFT'
        
        return is_submitter and is_draft
    
    def _can_edit_review(self, user, credit_request):
        """
        Check if the user can edit the credit review.
        Only credit analysts can edit, and only in CREDIT_REVIEW state.
        """
        # Check if the user is the assigned analyst
        is_analyst = user == credit_request.assigned_analyst
        
        # Check if the request is in CREDIT_REVIEW state
        is_review_state = credit_request.workflow_state.name == 'CREDIT_REVIEW'
        
        return is_analyst and is_review_state
    
    def _can_edit_sponsorship(self, user, credit_request):
        """
        Check if the user can edit the business sponsorship.
        Only business sponsors can edit, and only in BUSINESS_SPONSORSHIP_PENDING state.
        """
        # Check if the user is the business sponsor
        is_sponsor = user == credit_request.business_sponsor
        
        # Check if the request is in BUSINESS_SPONSORSHIP_PENDING state
        is_sponsorship_state = credit_request.workflow_state.name == 'BUSINESS_SPONSORSHIP_PENDING'
        
        return is_sponsor and is_sponsorship_state
    
    def _can_edit_questionnaire(self, user, credit_request):
        """
        Check if the user can edit the credit questionnaire.
        Only relationship managers can edit, and only if questionnaire is required
        and the request is in the right state.
        """
        # Check if questionnaire is required
        if not hasattr(credit_request, 'questionnaire_required') or not credit_request.questionnaire_required:
            return False
        
        # Check if the user is the submitter
        is_submitter = user == credit_request.submitter
        
        # Check if the request is in a state where questionnaire can be edited
        is_questionnaire_state = (
            credit_request.workflow_state.name == 'QUESTIONNAIRE_PENDING' or
            credit_request.workflow_state.name == 'QUESTIONNAIRE_DRAFT'
        )
        
        return is_submitter and is_questionnaire_state
    
    def _can_edit_legal(self, user, credit_request):
        """
        Check if the user can edit the legal review.
        Only legal reviewers can edit, and only in LEGAL_REVIEW_IN_PROGRESS state.
        """
        # Check if user has legal reviewer role
        has_legal_role = hasattr(user, 'role') and getattr(user, 'role', None) == 'LEGAL_REVIEWER'
        
        # Check if the request is in LEGAL_REVIEW_IN_PROGRESS state
        is_legal_review_state = (
            credit_request.workflow_state.name == 'LEGAL_REVIEW_IN_PROGRESS' or
            credit_request.workflow_state.name == 'LEGAL_REVIEW_DRAFT'
        )
        
        return has_legal_role and is_legal_review_state
    
    def _can_edit_analysis(self, user, credit_request):
        """
        Check if the user can edit the credit analysis.
        Only assigned credit analysts can edit, and only in CREDIT_ANALYSIS_IN_PROGRESS state.
        """
        # Check if the user is the assigned analyst
        is_analyst = user == credit_request.assigned_analyst
        
        # Check if the request is in CREDIT_ANALYSIS_IN_PROGRESS state
        is_analysis_state = (
            credit_request.workflow_state.name == 'CREDIT_ANALYSIS_IN_PROGRESS' or
            credit_request.workflow_state.name == 'CREDIT_ANALYSIS_DRAFT'
        )
        
        return is_analyst and is_analysis_state
