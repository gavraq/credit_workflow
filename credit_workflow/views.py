from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.utils import timezone
from django.contrib import messages
from django.db import models
from workflow.models import WorkflowState
from django.forms import inlineformset_factory
from .models import CreditRequest, CreditLimit, CreditQuestionnaire, LegalReview, Document, Notification, NotificationPreference, CreditAnalysis
from .forms import CreditRequestForm, CreditLimitForm, CreditReviewForm, CreditQuestionnaireForm, LegalReviewForm, DocumentForm, NotificationPreferenceForm, CreditAnalysisForm

# Import the DetailView implementation from the detailview file
from .views_detailview import CreditRequestDetailView

# Dashboard landing page
class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard landing page for the Credit Risk Workflow app."""
    template_name = "credit_workflow/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get requests submitted by the user or assigned to them
        user_requests = CreditRequest.objects.filter(submitter=self.request.user).order_by('-created_at')[:10]
        assigned_requests = CreditRequest.objects.filter(assigned_analyst=self.request.user).order_by('-created_at')[:10]
        
        # Combine the querysets and get unique values
        recent_requests = (user_requests | assigned_requests).distinct().order_by('-created_at')[:10]
        
        # If the above doesn't return any results, show all requests (for admin/testing)
        if not recent_requests and self.request.user.is_staff:
            recent_requests = CreditRequest.objects.all().order_by('-created_at')[:10]
            
        context['recent_requests'] = recent_requests
        
        # Add workflow stats
        context['workflow_states'] = WorkflowState.objects.all()
        context['total_requests'] = CreditRequest.objects.count()
        
        # Calculate counts for various states
        try:
            pending_approval_states = WorkflowState.objects.filter(name__in=["PENDING_APPROVAL", "BUSINESS_SPONSORSHIP_PENDING"])
            context['pending_approval_count'] = CreditRequest.objects.filter(workflow_state__in=pending_approval_states).count()
        except:
            context['pending_approval_count'] = 0
            
        try:
            context['awaiting_sponsorship_count'] = CreditRequest.objects.filter(workflow_state__name="BUSINESS_SPONSORSHIP_PENDING").count()
        except:
            context['awaiting_sponsorship_count'] = 0
            
        from django.utils import timezone
        start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        try:
            completed_states = WorkflowState.objects.filter(name__in=["APPROVED", "COMPLETED"])
            context['completed_this_month'] = CreditRequest.objects.filter(
                workflow_state__in=completed_states,
                updated_at__gte=start_of_month
            ).count()
        except:
            context['completed_this_month'] = 0
            
        return context

# Welcome view remains
def welcome(request):
    return render(request, 'credit_workflow/welcome.html')

class CreditRequestListView(LoginRequiredMixin, ListView):
    model = CreditRequest
    template_name = 'credit_workflow/creditrequest_list.html'
    context_object_name = 'credit_requests'
    paginate_by = 20
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Apply filters based on GET parameters
        status = self.request.GET.get('status')
        priority = self.request.GET.get('priority')
        counterparty = self.request.GET.get('counterparty')
        submitter = self.request.GET.get('submitter')
        
        if status:
            queryset = queryset.filter(workflow_state__name=status)
        
        if priority:
            queryset = queryset.filter(priority=priority)
        
        if counterparty:
            queryset = queryset.filter(counterparty__name__icontains=counterparty)
        
        if submitter:
            queryset = queryset.filter(
                models.Q(submitter__username__icontains=submitter) |
                models.Q(submitter__first_name__icontains=submitter) |
                models.Q(submitter__last_name__icontains=submitter)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add filter parameters to context for form persistence
        context['filters'] = {
            'status': self.request.GET.get('status', ''),
            'priority': self.request.GET.get('priority', ''),
            'counterparty': self.request.GET.get('counterparty', ''),
            'submitter': self.request.GET.get('submitter', ''),
        }
        return context

class CreditQuestionnaireCreateView(LoginRequiredMixin, CreateView):
    model = CreditQuestionnaire
    form_class = CreditQuestionnaireForm
    template_name = 'credit_workflow/creditquestionnaire_form.html'
    success_url = reverse_lazy('creditrequest_list')

    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill the credit_request if provided in URL
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        # Pre-fill the author with the current user
        initial['author'] = self.request.user
        return initial

    def form_valid(self, form):
        # Set the author to the current user
        form.instance.author = self.request.user
        
        # Set draft status based on which button was clicked
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Format the content field properly before saving
        content = self._format_questionnaire_content(form)
        if content:
            form.instance.content = content
            
        # Log the content for debugging
        print(f"DEBUG - Creating questionnaire with content: {form.instance.content[:200]}...")
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
        
    def _format_questionnaire_content(self, form):
        """
        Format the questionnaire content to ensure proper markdown formatting.
        """
        # Get the raw content from form data
        content = form.cleaned_data.get('content')
        if not content:
            return ""
            
        # Ensure section headers use proper markdown formatting
        import re
        # Check for section headers without markdown (all caps)
        section_pattern = r'^([A-Z][A-Z\s\'\/#]+)\s*'
        
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line is a section header without markdown
            if re.match(section_pattern, line.strip()) and not line.strip().startswith('#'):
                # Add proper markdown to section headers
                formatted_lines.append(f"## {line.strip()}")
            # Check if this line could be a field header without markdown
            elif i > 0 and line.strip() and ': ' in line and not line.strip().startswith('#'):
                # Add proper markdown to field headers
                field_name = line.split(':', 1)[0].strip()
                formatted_lines.append(f"### {field_name}")
                # Add the rest of the line after the colon
                rest = line.split(':', 1)[1].strip()
                if rest:
                    formatted_lines.append(rest)
            else:
                formatted_lines.append(line)
        
        # Join the lines back together
        formatted_content = '\n'.join(formatted_lines)
        
        # Ensure proper spacing between sections (double newline after section header)
        formatted_content = re.sub(r'(## [^\n]+)\n([^\n])', r'\1\n\n\2', formatted_content)
        
        # Ensure proper spacing between fields (single newline after field header)
        formatted_content = re.sub(r'(### [^\n]+)\n([^\n])', r'\1\n\2', formatted_content)
        
        return formatted_content
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditQuestionnaireUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditQuestionnaire
    form_class = CreditQuestionnaireForm
    template_name = 'credit_workflow/creditquestionnaire_form.html'

    def form_valid(self, form):
        # Set draft status based on which button was clicked
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Make sure the author is set
        if not form.instance.author_id:
            form.instance.author = self.request.user
        
        # Format the content field properly before saving
        content = self._format_questionnaire_content(form)
        if content:
            form.instance.content = content
        
        # Log the content for debugging
        print(f"DEBUG - Updating questionnaire with content: {form.instance.content[:200]}...")
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _format_questionnaire_content(self, form):
        """
        Format the questionnaire content to ensure proper markdown formatting.
        """
        # Get the raw content from form data
        content = form.cleaned_data.get('content')
        if not content:
            return ""
            
        # Ensure section headers use proper markdown formatting
        import re
        # Check for section headers without markdown (all caps)
        section_pattern = r'^([A-Z][A-Z\s\'\/#]+)\s*'
        
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line is a section header without markdown
            if re.match(section_pattern, line.strip()) and not line.strip().startswith('#'):
                # Add proper markdown to section headers
                formatted_lines.append(f"## {line.strip()}")
            # Check if this line could be a field header without markdown
            elif i > 0 and line.strip() and ': ' in line and not line.strip().startswith('#'):
                # Add proper markdown to field headers
                field_name = line.split(':', 1)[0].strip()
                formatted_lines.append(f"### {field_name}")
                # Add the rest of the line after the colon
                rest = line.split(':', 1)[1].strip()
                if rest:
                    formatted_lines.append(rest)
            else:
                formatted_lines.append(line)
        
        # Join the lines back together
        formatted_content = '\n'.join(formatted_lines)
        
        # Ensure proper spacing between sections (double newline after section header)
        formatted_content = re.sub(r'(## [^\n]+)\n([^\n])', r'\1\n\n\2', formatted_content)
        
        # Ensure proper spacing between fields (single newline after field header)
        formatted_content = re.sub(r'(### [^\n]+)\n([^\n])', r'\1\n\2', formatted_content)
        
        return formatted_content
        
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire updated and saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class DebugQuestionnaireView(LoginRequiredMixin, View):
    """
    Debug view to directly display questionnaire content and parsing results.
    This is for troubleshooting only.
    """
    template_name = 'credit_workflow/debug_questionnaire.html'
    
    def get(self, request, pk):
        questionnaire = get_object_or_404(CreditQuestionnaire, pk=pk)
        
        # Parse sections for debugging
        from credit_workflow.templatetags.credit_workflow_extras import parse_markdown_sections
        parsed_sections = parse_markdown_sections(questionnaire.content)
        
        # Add debug info
        context = {
            'questionnaire': questionnaire,
            'parsed_sections': parsed_sections,
            'business_model_details': questionnaire.business_model_details,
            'key_suppliers_customers': questionnaire.key_suppliers_customers,
            'trading_activity_rationale': questionnaire.trading_activity_rationale,
            'trading_policy_governance': questionnaire.trading_policy_governance,
            'liquidity_management': questionnaire.liquidity_management,
        }
        
        return render(request, self.template_name, context)

class LegalReviewCreateView(LoginRequiredMixin, CreateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_initial(self):
        """Pre-select the Credit Request if provided in the URL query parameters."""
        initial = super().get_initial()
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

class LegalReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

# Inline formset for CreditLimit
CreditLimitFormSet = inlineformset_factory(
    CreditRequest, CreditLimit, form=CreditLimitForm, extra=1, can_delete=True
)

from django.views.generic import DetailView

class CreditRequestConfirmationView(DetailView):
    model = CreditRequest
    template_name = 'credit_workflow/creditrequest_confirmation.html'
    context_object_name = 'credit_request'

class CreditRequestCreateView(CreateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST)
        else:
            context['limit_formset'] = CreditLimitFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            # Set workflow state based on submission type
            if not self.object.workflow_state_id:
                try:
                    if 'save_draft' in self.request.POST:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                    else:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Submitted")
                except WorkflowState.DoesNotExist:
                    # Fallback: set to first available state
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.submitted_at = timezone.now()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditRequestUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST, instance=self.object)
        else:
            context['limit_formset'] = CreditLimitFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            if 'save_draft' in self.request.POST:
                try:
                    self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                except WorkflowState.DoesNotExist:
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditReviewUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditReviewForm
    template_name = "credit_workflow/creditreview_form.html"
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only allow access if current state is CREDIT_REVIEW
        if self.object.workflow_state.name != "CREDIT_REVIEW":
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # Transition workflow state to BUSINESS_SPONSORSHIP_PENDING
        try:
            next_state = WorkflowState.objects.get(name="BUSINESS_SPONSORSHIP_PENDING")
            self.object.workflow_state = next_state
            # Add timestamp for credit review completion
            self.object.credit_review_completed_at = timezone.now()
            self.object.save()
        except WorkflowState.DoesNotExist:
            pass  # Optionally, add error handling/logging here
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        return context

class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'credit_workflow/document_upload.html'
    success_url = reverse_lazy('creditrequest_list')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        # Redirect back to the credit request detail page if provided
        if self.object.credit_request:
            return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})
        return self.success_url

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'credit_workflow/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        credit_request_id = self.kwargs.get('credit_request_id')
        return Document.objects.filter(credit_request_id=credit_request_id)

class NotificationCenterView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'credit_workflow/notification_center.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationPreferencesView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = 'credit_workflow/notification_preferences.html'
    success_url = reverse_lazy('notification_center')

    def get_object(self, queryset=None):
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse

class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationDismissView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return HttpResponseRedirect(reverse('notification_center'))

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer

class NotificationListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class NotificationMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class NotificationDismissAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class CreditAnalysisCreateView(LoginRequiredMixin, CreateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill the credit_request if provided in URL
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial

    def form_valid(self, form):
        form.instance.analyst = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Organize all the form data into a structured format
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Extract data from the existing analysis to pre-populate form fields
        analysis = self.object.analysis
        
        # Example method to extract sections - this would need to be enhanced based on your
        # actual analysis structure
        # Here we're just demonstrating a simple parsing approach
        if '## EXECUTIVE SUMMARY' in analysis and '### Purpose of Application' in analysis:
            purpose_section = analysis.split('### Purpose of Application')[1].split('##')[0].strip()
            initial['purpose_of_application'] = purpose_section
        
        # Financial Summary & Rating
        if '## FINANCIAL SUMMARY' in analysis:
            financial_section = analysis.split('## FINANCIAL SUMMARY')[1].split('##')[0].strip()
            initial['financial_summary'] = financial_section
            
            # Try to extract rating from the heading
            for rating in self.form_class.RATING_CHOICES:
                if rating[0] in financial_section:
                    initial['current_rating'] = rating[0]
                    break
        
        # Key Risks
        if '## KEY RISKS' in analysis:
            risks_section = analysis.split('## KEY RISKS')[1].split('##')[0].strip()
            initial['key_risks'] = risks_section
        
        # Market Risk
        if '## MARKET RISK ANALYSIS' in analysis:
            market_section = analysis.split('## MARKET RISK ANALYSIS')[1].split('##')[0].strip()
            initial['market_risk_analysis'] = market_section
        
        # Credit Recommendation
        if '## CREDIT RECOMMENDATION' in analysis:
            rec_section = analysis.split('## CREDIT RECOMMENDATION')[1].split('##')[0].strip()
            initial['credit_recommendation'] = rec_section
        
        # Asset Quality
        if '## ASSET QUALITY' in analysis:
            asset_section = analysis.split('## ASSET QUALITY')[1].split('##')[0].strip()
            initial['asset_quality'] = asset_section
        
        # Profitability
        if '## PROFITABILITY' in analysis:
            prof_section = analysis.split('## PROFITABILITY')[1].split('##')[0].strip()
            initial['profitability_analysis'] = prof_section
        
        # Funding & Liquidity
        if '## FUNDING & LIQUIDITY' in analysis:
            funding_section = analysis.split('## FUNDING & LIQUIDITY')[1].split('##', 1)[0].strip()
            initial['funding_liquidity'] = funding_section
            
        return initial

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Same as in CreateView
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisDetailView(LoginRequiredMixin, DetailView):
    model = CreditAnalysis
    template_name = 'credit_workflow/creditanalysis_detail.html'
    context_object_name = 'analysis'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the credit request for additional context
        context['credit_request'] = self.object.credit_request
        return context

# Create a new AssignedRequestsView class
class AssignedRequestsView(LoginRequiredMixin, ListView):
    """View for requests assigned to the current user based on their role."""
    model = CreditRequest
    template_name = 'credit_workflow/assigned_requests.html'
    context_object_name = 'assigned_requests'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        # Determine the queryset based on the user's role
        if hasattr(user, 'role'):
            role = getattr(user, 'role', None)
            
            if role == 'RELATIONSHIP_MANAGER':
                # Relationship managers see their submitted requests
                queryset = CreditRequest.objects.filter(submitter=user)
            elif role == 'CREDIT_ANALYST':
                # Credit analysts see requests assigned to them
                queryset = CreditRequest.objects.filter(assigned_analyst=user)
            elif role == 'BUSINESS_SPONSOR':
                # Business sponsors see requests where they are the sponsor
                queryset = CreditRequest.objects.filter(business_sponsor=user)
            elif role == 'LEGAL_REVIEWER':
                # Legal reviewers see requests in legal review
                try:
                    legal_review_states = WorkflowState.objects.filter(
                        name__in=['LEGAL_REVIEW_IN_PROGRESS', 'LEGAL_REVIEW_DRAFT'])
                    queryset = CreditRequest.objects.filter(workflow_state__in=legal_review_states)
                except:
                    queryset = CreditRequest.objects.none()
            else:
                queryset = CreditRequest.objects.none()
        else:
            queryset = CreditRequest.objects.none()
        
        # Apply ordering
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = getattr(self.request.user, 'role', 'Unknown')
        return context

        
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line is a section header without markdown
            if re.match(section_pattern, line.strip()) and not line.strip().startswith('#'):
                # Add proper markdown to section headers
                formatted_lines.append(f"## {line.strip()}")
            # Check if this line could be a field header without markdown
            elif i > 0 and line.strip() and ': ' in line and not line.strip().startswith('#'):
                # Add proper markdown to field headers
                field_name = line.split(':', 1)[0].strip()
                formatted_lines.append(f"### {field_name}")
                # Add the rest of the line after the colon
                rest = line.split(':', 1)[1].strip()
                if rest:
                    formatted_lines.append(rest)
            else:
                formatted_lines.append(line)
        
        # Join the lines back together
        formatted_content = '\n'.join(formatted_lines)
        
        # Ensure proper spacing between sections (double newline after section header)
        formatted_content = re.sub(r'(## [^\n]+)\n([^\n])', r'\1\n\n\2', formatted_content)
        
        # Ensure proper spacing between fields (single newline after field header)
        formatted_content = re.sub(r'(### [^\n]+)\n([^\n])', r'\1\n\2', formatted_content)
        
        return formatted_content
        
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

# CreditQuestionnaireUpdateView moved above to avoid duplicate

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class DebugQuestionnaireView(LoginRequiredMixin, View):
    """
    Debug view to directly display questionnaire content and parsing results.
    This is for troubleshooting only.
    """
    template_name = 'credit_workflow/debug_questionnaire.html'
    
    def get(self, request, pk):
        questionnaire = get_object_or_404(CreditQuestionnaire, pk=pk)
        
        # Parse sections for debugging
        from credit_workflow.templatetags.credit_workflow_extras import parse_markdown_sections
        parsed_sections = parse_markdown_sections(questionnaire.content)
        
        # Add debug info
        context = {
            'questionnaire': questionnaire,
            'parsed_sections': parsed_sections,
            'business_model_details': questionnaire.business_model_details,
            'key_suppliers_customers': questionnaire.key_suppliers_customers,
            'trading_activity_rationale': questionnaire.trading_activity_rationale,
            'trading_policy_governance': questionnaire.trading_policy_governance,
            'liquidity_management': questionnaire.liquidity_management,
        }
        
        return render(request, self.template_name, context)

class LegalReviewCreateView(LoginRequiredMixin, CreateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_initial(self):
        """Pre-select the Credit Request if provided in the URL query parameters."""
        initial = super().get_initial()
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

class LegalReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

# Inline formset for CreditLimit
CreditLimitFormSet = inlineformset_factory(
    CreditRequest, CreditLimit, form=CreditLimitForm, extra=1, can_delete=True
)

from django.views.generic import DetailView

class CreditRequestConfirmationView(DetailView):
    model = CreditRequest
    template_name = 'credit_workflow/creditrequest_confirmation.html'
    context_object_name = 'credit_request'

class CreditRequestCreateView(CreateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST)
        else:
            context['limit_formset'] = CreditLimitFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            # Set workflow state based on submission type
            if not self.object.workflow_state_id:
                try:
                    if 'save_draft' in self.request.POST:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                    else:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Submitted")
                except WorkflowState.DoesNotExist:
                    # Fallback: set to first available state
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.submitted_at = timezone.now()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditRequestUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST, instance=self.object)
        else:
            context['limit_formset'] = CreditLimitFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            if 'save_draft' in self.request.POST:
                try:
                    self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                except WorkflowState.DoesNotExist:
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditReviewUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditReviewForm
    template_name = "credit_workflow/creditreview_form.html"
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only allow access if current state is CREDIT_REVIEW
        if self.object.workflow_state.name != "CREDIT_REVIEW":
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # Transition workflow state to BUSINESS_SPONSORSHIP_PENDING
        try:
            next_state = WorkflowState.objects.get(name="BUSINESS_SPONSORSHIP_PENDING")
            self.object.workflow_state = next_state
            # Add timestamp for credit review completion
            self.object.credit_review_completed_at = timezone.now()
            self.object.save()
        except WorkflowState.DoesNotExist:
            pass  # Optionally, add error handling/logging here
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        return context

class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'credit_workflow/document_upload.html'
    success_url = reverse_lazy('creditrequest_list')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        # Redirect back to the credit request detail page if provided
        if self.object.credit_request:
            return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})
        return self.success_url

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'credit_workflow/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        credit_request_id = self.kwargs.get('credit_request_id')
        return Document.objects.filter(credit_request_id=credit_request_id)

class NotificationCenterView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'credit_workflow/notification_center.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationPreferencesView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = 'credit_workflow/notification_preferences.html'
    success_url = reverse_lazy('notification_center')

    def get_object(self, queryset=None):
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse

class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationDismissView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return HttpResponseRedirect(reverse('notification_center'))

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer

class NotificationListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class NotificationMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class NotificationDismissAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class CreditAnalysisCreateView(LoginRequiredMixin, CreateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill the credit_request if provided in URL
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial

    def form_valid(self, form):
        form.instance.analyst = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Organize all the form data into a structured format
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Extract data from the existing analysis to pre-populate form fields
        analysis = self.object.analysis
        
        # Example method to extract sections - this would need to be enhanced based on your
        # actual analysis structure
        # Here we're just demonstrating a simple parsing approach
        if '## EXECUTIVE SUMMARY' in analysis and '### Purpose of Application' in analysis:
            purpose_section = analysis.split('### Purpose of Application')[1].split('##')[0].strip()
            initial['purpose_of_application'] = purpose_section
        
        # Financial Summary & Rating
        if '## FINANCIAL SUMMARY' in analysis:
            financial_section = analysis.split('## FINANCIAL SUMMARY')[1].split('##')[0].strip()
            initial['financial_summary'] = financial_section
            
            # Try to extract rating from the heading
            for rating in self.form_class.RATING_CHOICES:
                if rating[0] in financial_section:
                    initial['current_rating'] = rating[0]
                    break
        
        # Key Risks
        if '## KEY RISKS' in analysis:
            risks_section = analysis.split('## KEY RISKS')[1].split('##')[0].strip()
            initial['key_risks'] = risks_section
        
        # Market Risk
        if '## MARKET RISK ANALYSIS' in analysis:
            market_section = analysis.split('## MARKET RISK ANALYSIS')[1].split('##')[0].strip()
            initial['market_risk_analysis'] = market_section
        
        # Credit Recommendation
        if '## CREDIT RECOMMENDATION' in analysis:
            rec_section = analysis.split('## CREDIT RECOMMENDATION')[1].split('##')[0].strip()
            initial['credit_recommendation'] = rec_section
        
        # Asset Quality
        if '## ASSET QUALITY' in analysis:
            asset_section = analysis.split('## ASSET QUALITY')[1].split('##')[0].strip()
            initial['asset_quality'] = asset_section
        
        # Profitability
        if '## PROFITABILITY' in analysis:
            prof_section = analysis.split('## PROFITABILITY')[1].split('##')[0].strip()
            initial['profitability_analysis'] = prof_section
        
        # Funding & Liquidity
        if '## FUNDING & LIQUIDITY' in analysis:
            funding_section = analysis.split('## FUNDING & LIQUIDITY')[1].split('##', 1)[0].strip()
            initial['funding_liquidity'] = funding_section
            
        return initial

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Same as in CreateView
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisDetailView(LoginRequiredMixin, DetailView):
    model = CreditAnalysis
    template_name = 'credit_workflow/creditanalysis_detail.html'
    context_object_name = 'analysis'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the credit request for additional context
        context['credit_request'] = self.object.credit_request
        return context

# Create a new AssignedRequestsView class
class AssignedRequestsView(LoginRequiredMixin, ListView):
    """View for requests assigned to the current user based on their role."""
    model = CreditRequest
    template_name = 'credit_workflow/assigned_requests.html'
    context_object_name = 'assigned_requests'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        # Determine the queryset based on the user's role
        if hasattr(user, 'role'):
            role = getattr(user, 'role', None)
            
            if role == 'RELATIONSHIP_MANAGER':
                # Relationship managers see their submitted requests
                queryset = CreditRequest.objects.filter(submitter=user)
            elif role == 'CREDIT_ANALYST':
                # Credit analysts see requests assigned to them
                queryset = CreditRequest.objects.filter(assigned_analyst=user)
            elif role == 'BUSINESS_SPONSOR':
                # Business sponsors see requests where they are the sponsor
                queryset = CreditRequest.objects.filter(business_sponsor=user)
            elif role == 'LEGAL_REVIEWER':
                # Legal reviewers see requests in legal review
                try:
                    legal_review_states = WorkflowState.objects.filter(
                        name__in=['LEGAL_REVIEW_IN_PROGRESS', 'LEGAL_REVIEW_DRAFT'])
                    queryset = CreditRequest.objects.filter(workflow_state__in=legal_review_states)
                except:
                    queryset = CreditRequest.objects.none()
            else:
                queryset = CreditRequest.objects.none()
        else:
            queryset = CreditRequest.objects.none()
        
        # Apply ordering
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = getattr(self.request.user, 'role', 'Unknown')
        return context

        
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line is a section header without markdown
            if re.match(section_pattern, line.strip()) and not line.strip().startswith('#'):
                # Add proper markdown to section headers
                formatted_lines.append(f"## {line.strip()}")
            # Check if this line could be a field header without markdown
            elif i > 0 and line.strip() and ': ' in line and not line.strip().startswith('#'):
                # Add proper markdown to field headers
                field_name = line.split(':', 1)[0].strip()
                formatted_lines.append(f"### {field_name}")
                # Add the rest of the line after the colon
                rest = line.split(':', 1)[1].strip()
                if rest:
                    formatted_lines.append(rest)
            else:
                formatted_lines.append(line)
        
        # Join the lines back together
        formatted_content = '\n'.join(formatted_lines)
        
        # Ensure proper spacing between sections (double newline after section header)
        formatted_content = re.sub(r'(## [^\n]+)\n([^\n])', r'\1\n\n\2', formatted_content)
        
        # Ensure proper spacing between fields (single newline after field header)
        formatted_content = re.sub(r'(### [^\n]+)\n([^\n])', r'\1\n\2', formatted_content)
        
        return formatted_content
        
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})
        
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditQuestionnaireUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditQuestionnaire
    form_class = CreditQuestionnaireForm
    template_name = 'credit_workflow/creditquestionnaire_form.html'

    def form_valid(self, form):
        # Set draft status based on which button was clicked
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Make sure the author is set
        if not form.instance.author_id:
            form.instance.author = self.request.user
        
        # Ensure the content field is properly saved
        content = form.cleaned_data.get('content')
        if content:
            form.instance.content = content
        
        # Log the content for debugging
        print(f"DEBUG - Saving questionnaire content: {form.instance.content[:100]}...")
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire updated and saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class DebugQuestionnaireView(LoginRequiredMixin, View):
    """
    Debug view to directly display questionnaire content and parsing results.
    This is for troubleshooting only.
    """
    template_name = 'credit_workflow/debug_questionnaire.html'
    
    def get(self, request, pk):
        questionnaire = get_object_or_404(CreditQuestionnaire, pk=pk)
        
        # Parse sections for debugging
        from credit_workflow.templatetags.credit_workflow_extras import parse_markdown_sections
        parsed_sections = parse_markdown_sections(questionnaire.content)
        
        # Add debug info
        context = {
            'questionnaire': questionnaire,
            'parsed_sections': parsed_sections,
            'business_model_details': questionnaire.business_model_details,
            'key_suppliers_customers': questionnaire.key_suppliers_customers,
            'trading_activity_rationale': questionnaire.trading_activity_rationale,
            'trading_policy_governance': questionnaire.trading_policy_governance,
            'liquidity_management': questionnaire.liquidity_management,
        }
        
        return render(request, self.template_name, context)

class LegalReviewCreateView(LoginRequiredMixin, CreateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_initial(self):
        """Pre-select the Credit Request if provided in the URL query parameters."""
        initial = super().get_initial()
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

class LegalReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

# Inline formset for CreditLimit
CreditLimitFormSet = inlineformset_factory(
    CreditRequest, CreditLimit, form=CreditLimitForm, extra=1, can_delete=True
)

from django.views.generic import DetailView

class CreditRequestConfirmationView(DetailView):
    model = CreditRequest
    template_name = 'credit_workflow/creditrequest_confirmation.html'
    context_object_name = 'credit_request'

class CreditRequestCreateView(CreateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST)
        else:
            context['limit_formset'] = CreditLimitFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            # Set workflow state based on submission type
            if not self.object.workflow_state_id:
                try:
                    if 'save_draft' in self.request.POST:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                    else:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Submitted")
                except WorkflowState.DoesNotExist:
                    # Fallback: set to first available state
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.submitted_at = timezone.now()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditRequestUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST, instance=self.object)
        else:
            context['limit_formset'] = CreditLimitFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            if 'save_draft' in self.request.POST:
                try:
                    self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                except WorkflowState.DoesNotExist:
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditReviewUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditReviewForm
    template_name = "credit_workflow/creditreview_form.html"
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only allow access if current state is CREDIT_REVIEW
        if self.object.workflow_state.name != "CREDIT_REVIEW":
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # Transition workflow state to BUSINESS_SPONSORSHIP_PENDING
        try:
            next_state = WorkflowState.objects.get(name="BUSINESS_SPONSORSHIP_PENDING")
            self.object.workflow_state = next_state
            # Add timestamp for credit review completion
            self.object.credit_review_completed_at = timezone.now()
            self.object.save()
        except WorkflowState.DoesNotExist:
            pass  # Optionally, add error handling/logging here
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        return context

class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'credit_workflow/document_upload.html'
    success_url = reverse_lazy('creditrequest_list')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        # Redirect back to the credit request detail page if provided
        if self.object.credit_request:
            return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})
        return self.success_url

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'credit_workflow/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        credit_request_id = self.kwargs.get('credit_request_id')
        return Document.objects.filter(credit_request_id=credit_request_id)

class NotificationCenterView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'credit_workflow/notification_center.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationPreferencesView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = 'credit_workflow/notification_preferences.html'
    success_url = reverse_lazy('notification_center')

    def get_object(self, queryset=None):
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse

class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationDismissView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return HttpResponseRedirect(reverse('notification_center'))

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer

class NotificationListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class NotificationMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class NotificationDismissAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class CreditAnalysisCreateView(LoginRequiredMixin, CreateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill the credit_request if provided in URL
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial

    def form_valid(self, form):
        form.instance.analyst = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Organize all the form data into a structured format
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Extract data from the existing analysis to pre-populate form fields
        analysis = self.object.analysis
        
        # Example method to extract sections - this would need to be enhanced based on your
        # actual analysis structure
        # Here we're just demonstrating a simple parsing approach
        if '## EXECUTIVE SUMMARY' in analysis and '### Purpose of Application' in analysis:
            purpose_section = analysis.split('### Purpose of Application')[1].split('##')[0].strip()
            initial['purpose_of_application'] = purpose_section
        
        # Financial Summary & Rating
        if '## FINANCIAL SUMMARY' in analysis:
            financial_section = analysis.split('## FINANCIAL SUMMARY')[1].split('##')[0].strip()
            initial['financial_summary'] = financial_section
            
            # Try to extract rating from the heading
            for rating in self.form_class.RATING_CHOICES:
                if rating[0] in financial_section:
                    initial['current_rating'] = rating[0]
                    break
        
        # Key Risks
        if '## KEY RISKS' in analysis:
            risks_section = analysis.split('## KEY RISKS')[1].split('##')[0].strip()
            initial['key_risks'] = risks_section
        
        # Market Risk
        if '## MARKET RISK ANALYSIS' in analysis:
            market_section = analysis.split('## MARKET RISK ANALYSIS')[1].split('##')[0].strip()
            initial['market_risk_analysis'] = market_section
        
        # Credit Recommendation
        if '## CREDIT RECOMMENDATION' in analysis:
            rec_section = analysis.split('## CREDIT RECOMMENDATION')[1].split('##')[0].strip()
            initial['credit_recommendation'] = rec_section
        
        # Asset Quality
        if '## ASSET QUALITY' in analysis:
            asset_section = analysis.split('## ASSET QUALITY')[1].split('##')[0].strip()
            initial['asset_quality'] = asset_section
        
        # Profitability
        if '## PROFITABILITY' in analysis:
            prof_section = analysis.split('## PROFITABILITY')[1].split('##')[0].strip()
            initial['profitability_analysis'] = prof_section
        
        # Funding & Liquidity
        if '## FUNDING & LIQUIDITY' in analysis:
            funding_section = analysis.split('## FUNDING & LIQUIDITY')[1].split('##', 1)[0].strip()
            initial['funding_liquidity'] = funding_section
            
        return initial

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Same as in CreateView
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisDetailView(LoginRequiredMixin, DetailView):
    model = CreditAnalysis
    template_name = 'credit_workflow/creditanalysis_detail.html'
    context_object_name = 'analysis'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the credit request for additional context
        context['credit_request'] = self.object.credit_request
        return context

# Create a new AssignedRequestsView class
class AssignedRequestsView(LoginRequiredMixin, ListView):
    """View for requests assigned to the current user based on their role."""
    model = CreditRequest
    template_name = 'credit_workflow/assigned_requests.html'
    context_object_name = 'assigned_requests'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        # Determine the queryset based on the user's role
        if hasattr(user, 'role'):
            role = getattr(user, 'role', None)
            
            if role == 'RELATIONSHIP_MANAGER':
                # Relationship managers see their submitted requests
                queryset = CreditRequest.objects.filter(submitter=user)
            elif role == 'CREDIT_ANALYST':
                # Credit analysts see requests assigned to them
                queryset = CreditRequest.objects.filter(assigned_analyst=user)
            elif role == 'BUSINESS_SPONSOR':
                # Business sponsors see requests where they are the sponsor
                queryset = CreditRequest.objects.filter(business_sponsor=user)
            elif role == 'LEGAL_REVIEWER':
                # Legal reviewers see requests in legal review
                try:
                    legal_review_states = WorkflowState.objects.filter(
                        name__in=['LEGAL_REVIEW_IN_PROGRESS', 'LEGAL_REVIEW_DRAFT'])
                    queryset = CreditRequest.objects.filter(workflow_state__in=legal_review_states)
                except:
                    queryset = CreditRequest.objects.none()
            else:
                queryset = CreditRequest.objects.none()
        else:
            queryset = CreditRequest.objects.none()
        
        # Apply ordering
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = getattr(self.request.user, 'role', 'Unknown')
        return context

        
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line is a section header without markdown
            if re.match(section_pattern, line.strip()) and not line.strip().startswith('#'):
                # Add proper markdown to section headers
                formatted_lines.append(f"## {line.strip()}")
            # Check if this line could be a field header without markdown
            elif i > 0 and line.strip() and ': ' in line and not line.strip().startswith('#'):
                # Add proper markdown to field headers
                field_name = line.split(':', 1)[0].strip()
                formatted_lines.append(f"### {field_name}")
                # Add the rest of the line after the colon
                rest = line.split(':', 1)[1].strip()
                if rest:
                    formatted_lines.append(rest)
            else:
                formatted_lines.append(line)
        
        # Join the lines back together
        formatted_content = '\n'.join(formatted_lines)
        
        # Ensure proper spacing between sections (double newline after section header)
        formatted_content = re.sub(r'(## [^\n]+)\n([^\n])', r'\1\n\n\2', formatted_content)
        
        # Ensure proper spacing between fields (single newline after field header)
        formatted_content = re.sub(r'(### [^\n]+)\n([^\n])', r'\1\n\2', formatted_content)
        
        return formatted_content
        
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditQuestionnaireUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditQuestionnaire
    form_class = CreditQuestionnaireForm
    template_name = 'credit_workflow/creditquestionnaire_form.html'

    def form_valid(self, form):
        # Set draft status based on which button was clicked
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Make sure the author is set
        if not form.instance.author_id:
            form.instance.author = self.request.user
        
        # Ensure the content field is properly saved
        content = form.cleaned_data.get('content')
        if content:
            form.instance.content = content
        
        # Log the content for debugging
        print(f"DEBUG - Saving questionnaire content: {form.instance.content[:100]}...")
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire updated and saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class DebugQuestionnaireView(LoginRequiredMixin, View):
    """
    Debug view to directly display questionnaire content and parsing results.
    This is for troubleshooting only.
    """
    template_name = 'credit_workflow/debug_questionnaire.html'
    
    def get(self, request, pk):
        questionnaire = get_object_or_404(CreditQuestionnaire, pk=pk)
        
        # Parse sections for debugging
        from credit_workflow.templatetags.credit_workflow_extras import parse_markdown_sections
        parsed_sections = parse_markdown_sections(questionnaire.content)
        
        # Add debug info
        context = {
            'questionnaire': questionnaire,
            'parsed_sections': parsed_sections,
            'business_model_details': questionnaire.business_model_details,
            'key_suppliers_customers': questionnaire.key_suppliers_customers,
            'trading_activity_rationale': questionnaire.trading_activity_rationale,
            'trading_policy_governance': questionnaire.trading_policy_governance,
            'liquidity_management': questionnaire.liquidity_management,
        }
        
        return render(request, self.template_name, context)

class LegalReviewCreateView(LoginRequiredMixin, CreateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_initial(self):
        """Pre-select the Credit Request if provided in the URL query parameters."""
        initial = super().get_initial()
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

class LegalReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

# Inline formset for CreditLimit
CreditLimitFormSet = inlineformset_factory(
    CreditRequest, CreditLimit, form=CreditLimitForm, extra=1, can_delete=True
)

from django.views.generic import DetailView

class CreditRequestConfirmationView(DetailView):
    model = CreditRequest
    template_name = 'credit_workflow/creditrequest_confirmation.html'
    context_object_name = 'credit_request'

class CreditRequestCreateView(CreateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST)
        else:
            context['limit_formset'] = CreditLimitFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            # Set workflow state based on submission type
            if not self.object.workflow_state_id:
                try:
                    if 'save_draft' in self.request.POST:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                    else:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Submitted")
                except WorkflowState.DoesNotExist:
                    # Fallback: set to first available state
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.submitted_at = timezone.now()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditRequestUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST, instance=self.object)
        else:
            context['limit_formset'] = CreditLimitFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            if 'save_draft' in self.request.POST:
                try:
                    self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                except WorkflowState.DoesNotExist:
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditReviewUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditReviewForm
    template_name = "credit_workflow/creditreview_form.html"
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only allow access if current state is CREDIT_REVIEW
        if self.object.workflow_state.name != "CREDIT_REVIEW":
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # Transition workflow state to BUSINESS_SPONSORSHIP_PENDING
        try:
            next_state = WorkflowState.objects.get(name="BUSINESS_SPONSORSHIP_PENDING")
            self.object.workflow_state = next_state
            # Add timestamp for credit review completion
            self.object.credit_review_completed_at = timezone.now()
            self.object.save()
        except WorkflowState.DoesNotExist:
            pass  # Optionally, add error handling/logging here
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        return context

class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'credit_workflow/document_upload.html'
    success_url = reverse_lazy('creditrequest_list')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        # Redirect back to the credit request detail page if provided
        if self.object.credit_request:
            return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})
        return self.success_url

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'credit_workflow/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        credit_request_id = self.kwargs.get('credit_request_id')
        return Document.objects.filter(credit_request_id=credit_request_id)

class NotificationCenterView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'credit_workflow/notification_center.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationPreferencesView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = 'credit_workflow/notification_preferences.html'
    success_url = reverse_lazy('notification_center')

    def get_object(self, queryset=None):
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse

class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationDismissView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return HttpResponseRedirect(reverse('notification_center'))

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer

class NotificationListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class NotificationMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class NotificationDismissAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class CreditAnalysisCreateView(LoginRequiredMixin, CreateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill the credit_request if provided in URL
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial

    def form_valid(self, form):
        form.instance.analyst = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Organize all the form data into a structured format
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Extract data from the existing analysis to pre-populate form fields
        analysis = self.object.analysis
        
        # Example method to extract sections - this would need to be enhanced based on your
        # actual analysis structure
        # Here we're just demonstrating a simple parsing approach
        if '## EXECUTIVE SUMMARY' in analysis and '### Purpose of Application' in analysis:
            purpose_section = analysis.split('### Purpose of Application')[1].split('##')[0].strip()
            initial['purpose_of_application'] = purpose_section
        
        # Financial Summary & Rating
        if '## FINANCIAL SUMMARY' in analysis:
            financial_section = analysis.split('## FINANCIAL SUMMARY')[1].split('##')[0].strip()
            initial['financial_summary'] = financial_section
            
            # Try to extract rating from the heading
            for rating in self.form_class.RATING_CHOICES:
                if rating[0] in financial_section:
                    initial['current_rating'] = rating[0]
                    break
        
        # Key Risks
        if '## KEY RISKS' in analysis:
            risks_section = analysis.split('## KEY RISKS')[1].split('##')[0].strip()
            initial['key_risks'] = risks_section
        
        # Market Risk
        if '## MARKET RISK ANALYSIS' in analysis:
            market_section = analysis.split('## MARKET RISK ANALYSIS')[1].split('##')[0].strip()
            initial['market_risk_analysis'] = market_section
        
        # Credit Recommendation
        if '## CREDIT RECOMMENDATION' in analysis:
            rec_section = analysis.split('## CREDIT RECOMMENDATION')[1].split('##')[0].strip()
            initial['credit_recommendation'] = rec_section
        
        # Asset Quality
        if '## ASSET QUALITY' in analysis:
            asset_section = analysis.split('## ASSET QUALITY')[1].split('##')[0].strip()
            initial['asset_quality'] = asset_section
        
        # Profitability
        if '## PROFITABILITY' in analysis:
            prof_section = analysis.split('## PROFITABILITY')[1].split('##')[0].strip()
            initial['profitability_analysis'] = prof_section
        
        # Funding & Liquidity
        if '## FUNDING & LIQUIDITY' in analysis:
            funding_section = analysis.split('## FUNDING & LIQUIDITY')[1].split('##', 1)[0].strip()
            initial['funding_liquidity'] = funding_section
            
        return initial

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Same as in CreateView
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisDetailView(LoginRequiredMixin, DetailView):
    model = CreditAnalysis
    template_name = 'credit_workflow/creditanalysis_detail.html'
    context_object_name = 'analysis'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the credit request for additional context
        context['credit_request'] = self.object.credit_request
        return context

# Create a new AssignedRequestsView class
class AssignedRequestsView(LoginRequiredMixin, ListView):
    """View for requests assigned to the current user based on their role."""
    model = CreditRequest
    template_name = 'credit_workflow/assigned_requests.html'
    context_object_name = 'assigned_requests'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        # Determine the queryset based on the user's role
        if hasattr(user, 'role'):
            role = getattr(user, 'role', None)
            
            if role == 'RELATIONSHIP_MANAGER':
                # Relationship managers see their submitted requests
                queryset = CreditRequest.objects.filter(submitter=user)
            elif role == 'CREDIT_ANALYST':
                # Credit analysts see requests assigned to them
                queryset = CreditRequest.objects.filter(assigned_analyst=user)
            elif role == 'BUSINESS_SPONSOR':
                # Business sponsors see requests where they are the sponsor
                queryset = CreditRequest.objects.filter(business_sponsor=user)
            elif role == 'LEGAL_REVIEWER':
                # Legal reviewers see requests in legal review
                try:
                    legal_review_states = WorkflowState.objects.filter(
                        name__in=['LEGAL_REVIEW_IN_PROGRESS', 'LEGAL_REVIEW_DRAFT'])
                    queryset = CreditRequest.objects.filter(workflow_state__in=legal_review_states)
                except:
                    queryset = CreditRequest.objects.none()
            else:
                queryset = CreditRequest.objects.none()
        else:
            queryset = CreditRequest.objects.none()
        
        # Apply ordering
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = getattr(self.request.user, 'role', 'Unknown')
        return context

        
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line is a section header without markdown
            if re.match(section_pattern, line.strip()) and not line.strip().startswith('#'):
                # Add proper markdown to section headers
                formatted_lines.append(f"## {line.strip()}")
            # Check if this line could be a field header without markdown
            elif i > 0 and line.strip() and ': ' in line and not line.strip().startswith('#'):
                # Add proper markdown to field headers
                field_name = line.split(':', 1)[0].strip()
                formatted_lines.append(f"### {field_name}")
                # Add the rest of the line after the colon
                rest = line.split(':', 1)[1].strip()
                if rest:
                    formatted_lines.append(rest)
            else:
                formatted_lines.append(line)
        
        # Join the lines back together
        formatted_content = '\n'.join(formatted_lines)
        
        # Ensure proper spacing between sections (double newline after section header)
        formatted_content = re.sub(r'(## [^\n]+)\n([^\n])', r'\1\n\n\2', formatted_content)
        
        # Ensure proper spacing between fields (single newline after field header)
        formatted_content = re.sub(r'(### [^\n]+)\n([^\n])', r'\1\n\2', formatted_content)
        
        return formatted_content
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire updated and saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class DebugQuestionnaireView(LoginRequiredMixin, View):
    """
    Debug view to directly display questionnaire content and parsing results.
    This is for troubleshooting only.
    """
    template_name = 'credit_workflow/debug_questionnaire.html'
    
    def get(self, request, pk):
        questionnaire = get_object_or_404(CreditQuestionnaire, pk=pk)
        
        # Parse sections for debugging
        from credit_workflow.templatetags.credit_workflow_extras import parse_markdown_sections
        parsed_sections = parse_markdown_sections(questionnaire.content)
        
        # Add debug info
        context = {
            'questionnaire': questionnaire,
            'parsed_sections': parsed_sections,
            'business_model_details': questionnaire.business_model_details,
            'key_suppliers_customers': questionnaire.key_suppliers_customers,
            'trading_activity_rationale': questionnaire.trading_activity_rationale,
            'trading_policy_governance': questionnaire.trading_policy_governance,
            'liquidity_management': questionnaire.liquidity_management,
        }
        
        return render(request, self.template_name, context)

class LegalReviewCreateView(LoginRequiredMixin, CreateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_initial(self):
        """Pre-select the Credit Request if provided in the URL query parameters."""
        initial = super().get_initial()
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

class LegalReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

# Inline formset for CreditLimit
CreditLimitFormSet = inlineformset_factory(
    CreditRequest, CreditLimit, form=CreditLimitForm, extra=1, can_delete=True
)

from django.views.generic import DetailView

class CreditRequestConfirmationView(DetailView):
    model = CreditRequest
    template_name = 'credit_workflow/creditrequest_confirmation.html'
    context_object_name = 'credit_request'

class CreditRequestCreateView(CreateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST)
        else:
            context['limit_formset'] = CreditLimitFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            # Set workflow state based on submission type
            if not self.object.workflow_state_id:
                try:
                    if 'save_draft' in self.request.POST:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                    else:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Submitted")
                except WorkflowState.DoesNotExist:
                    # Fallback: set to first available state
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.submitted_at = timezone.now()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditRequestUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST, instance=self.object)
        else:
            context['limit_formset'] = CreditLimitFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            if 'save_draft' in self.request.POST:
                try:
                    self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                except WorkflowState.DoesNotExist:
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditReviewUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditReviewForm
    template_name = "credit_workflow/creditreview_form.html"
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only allow access if current state is CREDIT_REVIEW
        if self.object.workflow_state.name != "CREDIT_REVIEW":
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # Transition workflow state to BUSINESS_SPONSORSHIP_PENDING
        try:
            next_state = WorkflowState.objects.get(name="BUSINESS_SPONSORSHIP_PENDING")
            self.object.workflow_state = next_state
            # Add timestamp for credit review completion
            self.object.credit_review_completed_at = timezone.now()
            self.object.save()
        except WorkflowState.DoesNotExist:
            pass  # Optionally, add error handling/logging here
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        return context

class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'credit_workflow/document_upload.html'
    success_url = reverse_lazy('creditrequest_list')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        # Redirect back to the credit request detail page if provided
        if self.object.credit_request:
            return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})
        return self.success_url

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'credit_workflow/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        credit_request_id = self.kwargs.get('credit_request_id')
        return Document.objects.filter(credit_request_id=credit_request_id)

class NotificationCenterView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'credit_workflow/notification_center.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationPreferencesView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = 'credit_workflow/notification_preferences.html'
    success_url = reverse_lazy('notification_center')

    def get_object(self, queryset=None):
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse

class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationDismissView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return HttpResponseRedirect(reverse('notification_center'))

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer

class NotificationListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class NotificationMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class NotificationDismissAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class CreditAnalysisCreateView(LoginRequiredMixin, CreateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill the credit_request if provided in URL
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial

    def form_valid(self, form):
        form.instance.analyst = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Organize all the form data into a structured format
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Extract data from the existing analysis to pre-populate form fields
        analysis = self.object.analysis
        
        # Example method to extract sections - this would need to be enhanced based on your
        # actual analysis structure
        # Here we're just demonstrating a simple parsing approach
        if '## EXECUTIVE SUMMARY' in analysis and '### Purpose of Application' in analysis:
            purpose_section = analysis.split('### Purpose of Application')[1].split('##')[0].strip()
            initial['purpose_of_application'] = purpose_section
        
        # Financial Summary & Rating
        if '## FINANCIAL SUMMARY' in analysis:
            financial_section = analysis.split('## FINANCIAL SUMMARY')[1].split('##')[0].strip()
            initial['financial_summary'] = financial_section
            
            # Try to extract rating from the heading
            for rating in self.form_class.RATING_CHOICES:
                if rating[0] in financial_section:
                    initial['current_rating'] = rating[0]
                    break
        
        # Key Risks
        if '## KEY RISKS' in analysis:
            risks_section = analysis.split('## KEY RISKS')[1].split('##')[0].strip()
            initial['key_risks'] = risks_section
        
        # Market Risk
        if '## MARKET RISK ANALYSIS' in analysis:
            market_section = analysis.split('## MARKET RISK ANALYSIS')[1].split('##')[0].strip()
            initial['market_risk_analysis'] = market_section
        
        # Credit Recommendation
        if '## CREDIT RECOMMENDATION' in analysis:
            rec_section = analysis.split('## CREDIT RECOMMENDATION')[1].split('##')[0].strip()
            initial['credit_recommendation'] = rec_section
        
        # Asset Quality
        if '## ASSET QUALITY' in analysis:
            asset_section = analysis.split('## ASSET QUALITY')[1].split('##')[0].strip()
            initial['asset_quality'] = asset_section
        
        # Profitability
        if '## PROFITABILITY' in analysis:
            prof_section = analysis.split('## PROFITABILITY')[1].split('##')[0].strip()
            initial['profitability_analysis'] = prof_section
        
        # Funding & Liquidity
        if '## FUNDING & LIQUIDITY' in analysis:
            funding_section = analysis.split('## FUNDING & LIQUIDITY')[1].split('##', 1)[0].strip()
            initial['funding_liquidity'] = funding_section
            
        return initial

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Same as in CreateView
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisDetailView(LoginRequiredMixin, DetailView):
    model = CreditAnalysis
    template_name = 'credit_workflow/creditanalysis_detail.html'
    context_object_name = 'analysis'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the credit request for additional context
        context['credit_request'] = self.object.credit_request
        return context

# Create a new AssignedRequestsView class
class AssignedRequestsView(LoginRequiredMixin, ListView):
    """View for requests assigned to the current user based on their role."""
    model = CreditRequest
    template_name = 'credit_workflow/assigned_requests.html'
    context_object_name = 'assigned_requests'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        # Determine the queryset based on the user's role
        if hasattr(user, 'role'):
            role = getattr(user, 'role', None)
            
            if role == 'RELATIONSHIP_MANAGER':
                # Relationship managers see their submitted requests
                queryset = CreditRequest.objects.filter(submitter=user)
            elif role == 'CREDIT_ANALYST':
                # Credit analysts see requests assigned to them
                queryset = CreditRequest.objects.filter(assigned_analyst=user)
            elif role == 'BUSINESS_SPONSOR':
                # Business sponsors see requests where they are the sponsor
                queryset = CreditRequest.objects.filter(business_sponsor=user)
            elif role == 'LEGAL_REVIEWER':
                # Legal reviewers see requests in legal review
                try:
                    legal_review_states = WorkflowState.objects.filter(
                        name__in=['LEGAL_REVIEW_IN_PROGRESS', 'LEGAL_REVIEW_DRAFT'])
                    queryset = CreditRequest.objects.filter(workflow_state__in=legal_review_states)
                except:
                    queryset = CreditRequest.objects.none()
            else:
                queryset = CreditRequest.objects.none()
        else:
            queryset = CreditRequest.objects.none()
        
        # Apply ordering
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = getattr(self.request.user, 'role', 'Unknown')
        return context

        
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line is a section header without markdown
            if re.match(section_pattern, line.strip()) and not line.strip().startswith('#'):
                # Add proper markdown to section headers
                formatted_lines.append(f"## {line.strip()}")
            # Check if this line could be a field header without markdown
            elif i > 0 and line.strip() and ': ' in line and not line.strip().startswith('#'):
                # Add proper markdown to field headers
                field_name = line.split(':', 1)[0].strip()
                formatted_lines.append(f"### {field_name}")
                # Add the rest of the line after the colon
                rest = line.split(':', 1)[1].strip()
                if rest:
                    formatted_lines.append(rest)
            else:
                formatted_lines.append(line)
        
        # Join the lines back together
        formatted_content = '\n'.join(formatted_lines)
        
        # Ensure proper spacing between sections (double newline after section header)
        formatted_content = re.sub(r'(## [^\n]+)\n([^\n])', r'\1\n\n\2', formatted_content)
        
        # Ensure proper spacing between fields (single newline after field header)
        formatted_content = re.sub(r'(### [^\n]+)\n([^\n])', r'\1\n\2', formatted_content)
        
        return formatted_content
        
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditQuestionnaireUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditQuestionnaire
    form_class = CreditQuestionnaireForm
    template_name = 'credit_workflow/creditquestionnaire_form.html'

    def form_valid(self, form):
        # Set draft status based on which button was clicked
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Make sure the author is set
        if not form.instance.author_id:
            form.instance.author = self.request.user
        
        # Ensure the content field is properly saved
        content = form.cleaned_data.get('content')
        if content:
            form.instance.content = content
        
        # Log the content for debugging
        print(f"DEBUG - Saving questionnaire content: {form.instance.content[:100]}...")
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire updated and saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class DebugQuestionnaireView(LoginRequiredMixin, View):
    """
    Debug view to directly display questionnaire content and parsing results.
    This is for troubleshooting only.
    """
    template_name = 'credit_workflow/debug_questionnaire.html'
    
    def get(self, request, pk):
        questionnaire = get_object_or_404(CreditQuestionnaire, pk=pk)
        
        # Parse sections for debugging
        from credit_workflow.templatetags.credit_workflow_extras import parse_markdown_sections
        parsed_sections = parse_markdown_sections(questionnaire.content)
        
        # Add debug info
        context = {
            'questionnaire': questionnaire,
            'parsed_sections': parsed_sections,
            'business_model_details': questionnaire.business_model_details,
            'key_suppliers_customers': questionnaire.key_suppliers_customers,
            'trading_activity_rationale': questionnaire.trading_activity_rationale,
            'trading_policy_governance': questionnaire.trading_policy_governance,
            'liquidity_management': questionnaire.liquidity_management,
        }
        
        return render(request, self.template_name, context)

class LegalReviewCreateView(LoginRequiredMixin, CreateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_initial(self):
        """Pre-select the Credit Request if provided in the URL query parameters."""
        initial = super().get_initial()
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

class LegalReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

# Inline formset for CreditLimit
CreditLimitFormSet = inlineformset_factory(
    CreditRequest, CreditLimit, form=CreditLimitForm, extra=1, can_delete=True
)

from django.views.generic import DetailView

class CreditRequestConfirmationView(DetailView):
    model = CreditRequest
    template_name = 'credit_workflow/creditrequest_confirmation.html'
    context_object_name = 'credit_request'

class CreditRequestCreateView(CreateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST)
        else:
            context['limit_formset'] = CreditLimitFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            # Set workflow state based on submission type
            if not self.object.workflow_state_id:
                try:
                    if 'save_draft' in self.request.POST:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                    else:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Submitted")
                except WorkflowState.DoesNotExist:
                    # Fallback: set to first available state
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.submitted_at = timezone.now()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditRequestUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST, instance=self.object)
        else:
            context['limit_formset'] = CreditLimitFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            if 'save_draft' in self.request.POST:
                try:
                    self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                except WorkflowState.DoesNotExist:
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditReviewUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditReviewForm
    template_name = "credit_workflow/creditreview_form.html"
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only allow access if current state is CREDIT_REVIEW
        if self.object.workflow_state.name != "CREDIT_REVIEW":
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # Transition workflow state to BUSINESS_SPONSORSHIP_PENDING
        try:
            next_state = WorkflowState.objects.get(name="BUSINESS_SPONSORSHIP_PENDING")
            self.object.workflow_state = next_state
            # Add timestamp for credit review completion
            self.object.credit_review_completed_at = timezone.now()
            self.object.save()
        except WorkflowState.DoesNotExist:
            pass  # Optionally, add error handling/logging here
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        return context

class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'credit_workflow/document_upload.html'
    success_url = reverse_lazy('creditrequest_list')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        # Redirect back to the credit request detail page if provided
        if self.object.credit_request:
            return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})
        return self.success_url

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'credit_workflow/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        credit_request_id = self.kwargs.get('credit_request_id')
        return Document.objects.filter(credit_request_id=credit_request_id)

class NotificationCenterView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'credit_workflow/notification_center.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationPreferencesView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = 'credit_workflow/notification_preferences.html'
    success_url = reverse_lazy('notification_center')

    def get_object(self, queryset=None):
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse

class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationDismissView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return HttpResponseRedirect(reverse('notification_center'))

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer

class NotificationListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class NotificationMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class NotificationDismissAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class CreditAnalysisCreateView(LoginRequiredMixin, CreateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill the credit_request if provided in URL
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial

    def form_valid(self, form):
        form.instance.analyst = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Organize all the form data into a structured format
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Extract data from the existing analysis to pre-populate form fields
        analysis = self.object.analysis
        
        # Example method to extract sections - this would need to be enhanced based on your
        # actual analysis structure
        # Here we're just demonstrating a simple parsing approach
        if '## EXECUTIVE SUMMARY' in analysis and '### Purpose of Application' in analysis:
            purpose_section = analysis.split('### Purpose of Application')[1].split('##')[0].strip()
            initial['purpose_of_application'] = purpose_section
        
        # Financial Summary & Rating
        if '## FINANCIAL SUMMARY' in analysis:
            financial_section = analysis.split('## FINANCIAL SUMMARY')[1].split('##')[0].strip()
            initial['financial_summary'] = financial_section
            
            # Try to extract rating from the heading
            for rating in self.form_class.RATING_CHOICES:
                if rating[0] in financial_section:
                    initial['current_rating'] = rating[0]
                    break
        
        # Key Risks
        if '## KEY RISKS' in analysis:
            risks_section = analysis.split('## KEY RISKS')[1].split('##')[0].strip()
            initial['key_risks'] = risks_section
        
        # Market Risk
        if '## MARKET RISK ANALYSIS' in analysis:
            market_section = analysis.split('## MARKET RISK ANALYSIS')[1].split('##')[0].strip()
            initial['market_risk_analysis'] = market_section
        
        # Credit Recommendation
        if '## CREDIT RECOMMENDATION' in analysis:
            rec_section = analysis.split('## CREDIT RECOMMENDATION')[1].split('##')[0].strip()
            initial['credit_recommendation'] = rec_section
        
        # Asset Quality
        if '## ASSET QUALITY' in analysis:
            asset_section = analysis.split('## ASSET QUALITY')[1].split('##')[0].strip()
            initial['asset_quality'] = asset_section
        
        # Profitability
        if '## PROFITABILITY' in analysis:
            prof_section = analysis.split('## PROFITABILITY')[1].split('##')[0].strip()
            initial['profitability_analysis'] = prof_section
        
        # Funding & Liquidity
        if '## FUNDING & LIQUIDITY' in analysis:
            funding_section = analysis.split('## FUNDING & LIQUIDITY')[1].split('##', 1)[0].strip()
            initial['funding_liquidity'] = funding_section
            
        return initial

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Same as in CreateView
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisDetailView(LoginRequiredMixin, DetailView):
    model = CreditAnalysis
    template_name = 'credit_workflow/creditanalysis_detail.html'
    context_object_name = 'analysis'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the credit request for additional context
        context['credit_request'] = self.object.credit_request
        return context

# Create a new AssignedRequestsView class
class AssignedRequestsView(LoginRequiredMixin, ListView):
    """View for requests assigned to the current user based on their role."""
    model = CreditRequest
    template_name = 'credit_workflow/assigned_requests.html'
    context_object_name = 'assigned_requests'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        # Determine the queryset based on the user's role
        if hasattr(user, 'role'):
            role = getattr(user, 'role', None)
            
            if role == 'RELATIONSHIP_MANAGER':
                # Relationship managers see their submitted requests
                queryset = CreditRequest.objects.filter(submitter=user)
            elif role == 'CREDIT_ANALYST':
                # Credit analysts see requests assigned to them
                queryset = CreditRequest.objects.filter(assigned_analyst=user)
            elif role == 'BUSINESS_SPONSOR':
                # Business sponsors see requests where they are the sponsor
                queryset = CreditRequest.objects.filter(business_sponsor=user)
            elif role == 'LEGAL_REVIEWER':
                # Legal reviewers see requests in legal review
                try:
                    legal_review_states = WorkflowState.objects.filter(
                        name__in=['LEGAL_REVIEW_IN_PROGRESS', 'LEGAL_REVIEW_DRAFT'])
                    queryset = CreditRequest.objects.filter(workflow_state__in=legal_review_states)
                except:
                    queryset = CreditRequest.objects.none()
            else:
                queryset = CreditRequest.objects.none()
        else:
            queryset = CreditRequest.objects.none()
        
        # Apply ordering
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = getattr(self.request.user, 'role', 'Unknown')
        return context

        
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line is a section header without markdown
            if re.match(section_pattern, line.strip()) and not line.strip().startswith('#'):
                # Add proper markdown to section headers
                formatted_lines.append(f"## {line.strip()}")
            # Check if this line could be a field header without markdown
            elif i > 0 and line.strip() and ': ' in line and not line.strip().startswith('#'):
                # Add proper markdown to field headers
                field_name = line.split(':', 1)[0].strip()
                formatted_lines.append(f"### {field_name}")
                # Add the rest of the line after the colon
                rest = line.split(':', 1)[1].strip()
                if rest:
                    formatted_lines.append(rest)
            else:
                formatted_lines.append(line)
        
        # Join the lines back together
        formatted_content = '\n'.join(formatted_lines)
        
        # Ensure proper spacing between sections (double newline after section header)
        formatted_content = re.sub(r'(## [^\n]+)\n([^\n])', r'\1\n\n\2', formatted_content)
        
        # Ensure proper spacing between fields (single newline after field header)
        formatted_content = re.sub(r'(### [^\n]+)\n([^\n])', r'\1\n\2', formatted_content)
        
        return formatted_content
        
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})
        
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditQuestionnaireUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditQuestionnaire
    form_class = CreditQuestionnaireForm
    template_name = 'credit_workflow/creditquestionnaire_form.html'

    def form_valid(self, form):
        # Set draft status based on which button was clicked
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Make sure the author is set
        if not form.instance.author_id:
            form.instance.author = self.request.user
        
        # Ensure the content field is properly saved
        content = form.cleaned_data.get('content')
        if content:
            form.instance.content = content
        
        # Log the content for debugging
        print(f"DEBUG - Saving questionnaire content: {form.instance.content[:100]}...")
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire updated and saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class DebugQuestionnaireView(LoginRequiredMixin, View):
    """
    Debug view to directly display questionnaire content and parsing results.
    This is for troubleshooting only.
    """
    template_name = 'credit_workflow/debug_questionnaire.html'
    
    def get(self, request, pk):
        questionnaire = get_object_or_404(CreditQuestionnaire, pk=pk)
        
        # Parse sections for debugging
        from credit_workflow.templatetags.credit_workflow_extras import parse_markdown_sections
        parsed_sections = parse_markdown_sections(questionnaire.content)
        
        # Add debug info
        context = {
            'questionnaire': questionnaire,
            'parsed_sections': parsed_sections,
            'business_model_details': questionnaire.business_model_details,
            'key_suppliers_customers': questionnaire.key_suppliers_customers,
            'trading_activity_rationale': questionnaire.trading_activity_rationale,
            'trading_policy_governance': questionnaire.trading_policy_governance,
            'liquidity_management': questionnaire.liquidity_management,
        }
        
        return render(request, self.template_name, context)

class LegalReviewCreateView(LoginRequiredMixin, CreateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_initial(self):
        """Pre-select the Credit Request if provided in the URL query parameters."""
        initial = super().get_initial()
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

class LegalReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

# Inline formset for CreditLimit
CreditLimitFormSet = inlineformset_factory(
    CreditRequest, CreditLimit, form=CreditLimitForm, extra=1, can_delete=True
)

from django.views.generic import DetailView

class CreditRequestConfirmationView(DetailView):
    model = CreditRequest
    template_name = 'credit_workflow/creditrequest_confirmation.html'
    context_object_name = 'credit_request'

class CreditRequestCreateView(CreateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST)
        else:
            context['limit_formset'] = CreditLimitFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            # Set workflow state based on submission type
            if not self.object.workflow_state_id:
                try:
                    if 'save_draft' in self.request.POST:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                    else:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Submitted")
                except WorkflowState.DoesNotExist:
                    # Fallback: set to first available state
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.submitted_at = timezone.now()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditRequestUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST, instance=self.object)
        else:
            context['limit_formset'] = CreditLimitFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            if 'save_draft' in self.request.POST:
                try:
                    self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                except WorkflowState.DoesNotExist:
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditReviewUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditReviewForm
    template_name = "credit_workflow/creditreview_form.html"
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only allow access if current state is CREDIT_REVIEW
        if self.object.workflow_state.name != "CREDIT_REVIEW":
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # Transition workflow state to BUSINESS_SPONSORSHIP_PENDING
        try:
            next_state = WorkflowState.objects.get(name="BUSINESS_SPONSORSHIP_PENDING")
            self.object.workflow_state = next_state
            # Add timestamp for credit review completion
            self.object.credit_review_completed_at = timezone.now()
            self.object.save()
        except WorkflowState.DoesNotExist:
            pass  # Optionally, add error handling/logging here
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        return context

class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'credit_workflow/document_upload.html'
    success_url = reverse_lazy('creditrequest_list')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        # Redirect back to the credit request detail page if provided
        if self.object.credit_request:
            return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})
        return self.success_url

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'credit_workflow/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        credit_request_id = self.kwargs.get('credit_request_id')
        return Document.objects.filter(credit_request_id=credit_request_id)

class NotificationCenterView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'credit_workflow/notification_center.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationPreferencesView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = 'credit_workflow/notification_preferences.html'
    success_url = reverse_lazy('notification_center')

    def get_object(self, queryset=None):
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse

class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationDismissView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return HttpResponseRedirect(reverse('notification_center'))

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer

class NotificationListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class NotificationMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class NotificationDismissAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class CreditAnalysisCreateView(LoginRequiredMixin, CreateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill the credit_request if provided in URL
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial

    def form_valid(self, form):
        form.instance.analyst = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Organize all the form data into a structured format
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Extract data from the existing analysis to pre-populate form fields
        analysis = self.object.analysis
        
        # Example method to extract sections - this would need to be enhanced based on your
        # actual analysis structure
        # Here we're just demonstrating a simple parsing approach
        if '## EXECUTIVE SUMMARY' in analysis and '### Purpose of Application' in analysis:
            purpose_section = analysis.split('### Purpose of Application')[1].split('##')[0].strip()
            initial['purpose_of_application'] = purpose_section
        
        # Financial Summary & Rating
        if '## FINANCIAL SUMMARY' in analysis:
            financial_section = analysis.split('## FINANCIAL SUMMARY')[1].split('##')[0].strip()
            initial['financial_summary'] = financial_section
            
            # Try to extract rating from the heading
            for rating in self.form_class.RATING_CHOICES:
                if rating[0] in financial_section:
                    initial['current_rating'] = rating[0]
                    break
        
        # Key Risks
        if '## KEY RISKS' in analysis:
            risks_section = analysis.split('## KEY RISKS')[1].split('##')[0].strip()
            initial['key_risks'] = risks_section
        
        # Market Risk
        if '## MARKET RISK ANALYSIS' in analysis:
            market_section = analysis.split('## MARKET RISK ANALYSIS')[1].split('##')[0].strip()
            initial['market_risk_analysis'] = market_section
        
        # Credit Recommendation
        if '## CREDIT RECOMMENDATION' in analysis:
            rec_section = analysis.split('## CREDIT RECOMMENDATION')[1].split('##')[0].strip()
            initial['credit_recommendation'] = rec_section
        
        # Asset Quality
        if '## ASSET QUALITY' in analysis:
            asset_section = analysis.split('## ASSET QUALITY')[1].split('##')[0].strip()
            initial['asset_quality'] = asset_section
        
        # Profitability
        if '## PROFITABILITY' in analysis:
            prof_section = analysis.split('## PROFITABILITY')[1].split('##')[0].strip()
            initial['profitability_analysis'] = prof_section
        
        # Funding & Liquidity
        if '## FUNDING & LIQUIDITY' in analysis:
            funding_section = analysis.split('## FUNDING & LIQUIDITY')[1].split('##', 1)[0].strip()
            initial['funding_liquidity'] = funding_section
            
        return initial

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Same as in CreateView
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisDetailView(LoginRequiredMixin, DetailView):
    model = CreditAnalysis
    template_name = 'credit_workflow/creditanalysis_detail.html'
    context_object_name = 'analysis'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the credit request for additional context
        context['credit_request'] = self.object.credit_request
        return context

# Create a new AssignedRequestsView class
class AssignedRequestsView(LoginRequiredMixin, ListView):
    """View for requests assigned to the current user based on their role."""
    model = CreditRequest
    template_name = 'credit_workflow/assigned_requests.html'
    context_object_name = 'assigned_requests'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        # Determine the queryset based on the user's role
        if hasattr(user, 'role'):
            role = getattr(user, 'role', None)
            
            if role == 'RELATIONSHIP_MANAGER':
                # Relationship managers see their submitted requests
                queryset = CreditRequest.objects.filter(submitter=user)
            elif role == 'CREDIT_ANALYST':
                # Credit analysts see requests assigned to them
                queryset = CreditRequest.objects.filter(assigned_analyst=user)
            elif role == 'BUSINESS_SPONSOR':
                # Business sponsors see requests where they are the sponsor
                queryset = CreditRequest.objects.filter(business_sponsor=user)
            elif role == 'LEGAL_REVIEWER':
                # Legal reviewers see requests in legal review
                try:
                    legal_review_states = WorkflowState.objects.filter(
                        name__in=['LEGAL_REVIEW_IN_PROGRESS', 'LEGAL_REVIEW_DRAFT'])
                    queryset = CreditRequest.objects.filter(workflow_state__in=legal_review_states)
                except:
                    queryset = CreditRequest.objects.none()
            else:
                queryset = CreditRequest.objects.none()
        else:
            queryset = CreditRequest.objects.none()
        
        # Apply ordering
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = getattr(self.request.user, 'role', 'Unknown')
        return context

        
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line is a section header without markdown
            if re.match(section_pattern, line.strip()) and not line.strip().startswith('#'):
                # Add proper markdown to section headers
                formatted_lines.append(f"## {line.strip()}")
            # Check if this line could be a field header without markdown
            elif i > 0 and line.strip() and ': ' in line and not line.strip().startswith('#'):
                # Add proper markdown to field headers
                field_name = line.split(':', 1)[0].strip()
                formatted_lines.append(f"### {field_name}")
                # Add the rest of the line after the colon
                rest = line.split(':', 1)[1].strip()
                if rest:
                    formatted_lines.append(rest)
            else:
                formatted_lines.append(line)
        
        # Join the lines back together
        formatted_content = '\n'.join(formatted_lines)
        
        # Ensure proper spacing between sections (double newline after section header)
        formatted_content = re.sub(r'(## [^\n]+)\n([^\n])', r'\1\n\n\2', formatted_content)
        
        # Ensure proper spacing between fields (single newline after field header)
        formatted_content = re.sub(r'(### [^\n]+)\n([^\n])', r'\1\n\2', formatted_content)
        
        return formatted_content
        
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditQuestionnaireUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditQuestionnaire
    form_class = CreditQuestionnaireForm
    template_name = 'credit_workflow/creditquestionnaire_form.html'

    def form_valid(self, form):
        # Set draft status based on which button was clicked
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Make sure the author is set
        if not form.instance.author_id:
            form.instance.author = self.request.user
        
        # Ensure the content field is properly saved
        content = form.cleaned_data.get('content')
        if content:
            form.instance.content = content
        
        # Log the content for debugging
        print(f"DEBUG - Saving questionnaire content: {form.instance.content[:100]}...")
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Questionnaire updated and saved as draft.')
        else:
            messages.success(self.request, 'Questionnaire updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class DebugQuestionnaireView(LoginRequiredMixin, View):
    """
    Debug view to directly display questionnaire content and parsing results.
    This is for troubleshooting only.
    """
    template_name = 'credit_workflow/debug_questionnaire.html'
    
    def get(self, request, pk):
        questionnaire = get_object_or_404(CreditQuestionnaire, pk=pk)
        
        # Parse sections for debugging
        from credit_workflow.templatetags.credit_workflow_extras import parse_markdown_sections
        parsed_sections = parse_markdown_sections(questionnaire.content)
        
        # Add debug info
        context = {
            'questionnaire': questionnaire,
            'parsed_sections': parsed_sections,
            'business_model_details': questionnaire.business_model_details,
            'key_suppliers_customers': questionnaire.key_suppliers_customers,
            'trading_activity_rationale': questionnaire.trading_activity_rationale,
            'trading_policy_governance': questionnaire.trading_policy_governance,
            'liquidity_management': questionnaire.liquidity_management,
        }
        
        return render(request, self.template_name, context)

class LegalReviewCreateView(LoginRequiredMixin, CreateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_initial(self):
        """Pre-select the Credit Request if provided in the URL query parameters."""
        initial = super().get_initial()
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

class LegalReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = LegalReview
    form_class = LegalReviewForm
    template_name = 'credit_workflow/legalreview_form.html'
    
    def get_success_url(self):
        """Redirect to the credit request detail page after successful submission."""
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response

# Inline formset for CreditLimit
CreditLimitFormSet = inlineformset_factory(
    CreditRequest, CreditLimit, form=CreditLimitForm, extra=1, can_delete=True
)

from django.views.generic import DetailView

class CreditRequestConfirmationView(DetailView):
    model = CreditRequest
    template_name = 'credit_workflow/creditrequest_confirmation.html'
    context_object_name = 'credit_request'

class CreditRequestCreateView(CreateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST)
        else:
            context['limit_formset'] = CreditLimitFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            # Set workflow state based on submission type
            if not self.object.workflow_state_id:
                try:
                    if 'save_draft' in self.request.POST:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                    else:
                        self.object.workflow_state = WorkflowState.objects.get(name__iexact="Submitted")
                except WorkflowState.DoesNotExist:
                    # Fallback: set to first available state
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.submitted_at = timezone.now()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditRequestUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditRequestForm
    template_name = 'credit_workflow/creditrequest_form.html'
    success_url = reverse_lazy('welcome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['limit_formset'] = CreditLimitFormSet(self.request.POST, instance=self.object)
        else:
            context['limit_formset'] = CreditLimitFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        limit_formset = context['limit_formset']
        if form.is_valid() and limit_formset.is_valid():
            self.object = form.save(commit=False)
            if 'save_draft' in self.request.POST:
                try:
                    self.object.workflow_state = WorkflowState.objects.get(name__iexact="Draft")
                except WorkflowState.DoesNotExist:
                    self.object.workflow_state = WorkflowState.objects.first()
            self.object.save()
            limit_formset.instance = self.object
            limit_formset.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CreditReviewUpdateView(UpdateView):
    model = CreditRequest
    form_class = CreditReviewForm
    template_name = "credit_workflow/creditreview_form.html"
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only allow access if current state is CREDIT_REVIEW
        if self.object.workflow_state.name != "CREDIT_REVIEW":
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # Transition workflow state to BUSINESS_SPONSORSHIP_PENDING
        try:
            next_state = WorkflowState.objects.get(name="BUSINESS_SPONSORSHIP_PENDING")
            self.object.workflow_state = next_state
            # Add timestamp for credit review completion
            self.object.credit_review_completed_at = timezone.now()
            self.object.save()
        except WorkflowState.DoesNotExist:
            pass  # Optionally, add error handling/logging here
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        return context

class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'credit_workflow/document_upload.html'
    success_url = reverse_lazy('creditrequest_list')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def get_success_url(self):
        # Redirect back to the credit request detail page if provided
        if self.object.credit_request:
            return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})
        return self.success_url

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'credit_workflow/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        credit_request_id = self.kwargs.get('credit_request_id')
        return Document.objects.filter(credit_request_id=credit_request_id)

class NotificationCenterView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'credit_workflow/notification_center.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationPreferencesView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = 'credit_workflow/notification_preferences.html'
    success_url = reverse_lazy('notification_center')

    def get_object(self, queryset=None):
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse

class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationDismissView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
        return HttpResponseRedirect(reverse('notification_center'))

class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return HttpResponseRedirect(reverse('notification_center'))

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer

class NotificationListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class NotificationMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.read = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class NotificationDismissAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(pk=pk, user=request.user).first()
        if notification:
            notification.dismissed = True
            notification.save()
            return Response({'status': 'success'})
        return Response({'status': 'not found'}, status=404)

class CreditAnalysisCreateView(LoginRequiredMixin, CreateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill the credit_request if provided in URL
        credit_request_id = self.request.GET.get('credit_request')
        if credit_request_id:
            initial['credit_request'] = credit_request_id
        return initial

    def form_valid(self, form):
        form.instance.analyst = self.request.user
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Organize all the form data into a structured format
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    model = CreditAnalysis
    form_class = CreditAnalysisForm
    template_name = 'credit_workflow/creditanalysis_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Extract data from the existing analysis to pre-populate form fields
        analysis = self.object.analysis
        
        # Example method to extract sections - this would need to be enhanced based on your
        # actual analysis structure
        # Here we're just demonstrating a simple parsing approach
        if '## EXECUTIVE SUMMARY' in analysis and '### Purpose of Application' in analysis:
            purpose_section = analysis.split('### Purpose of Application')[1].split('##')[0].strip()
            initial['purpose_of_application'] = purpose_section
        
        # Financial Summary & Rating
        if '## FINANCIAL SUMMARY' in analysis:
            financial_section = analysis.split('## FINANCIAL SUMMARY')[1].split('##')[0].strip()
            initial['financial_summary'] = financial_section
            
            # Try to extract rating from the heading
            for rating in self.form_class.RATING_CHOICES:
                if rating[0] in financial_section:
                    initial['current_rating'] = rating[0]
                    break
        
        # Key Risks
        if '## KEY RISKS' in analysis:
            risks_section = analysis.split('## KEY RISKS')[1].split('##')[0].strip()
            initial['key_risks'] = risks_section
        
        # Market Risk
        if '## MARKET RISK ANALYSIS' in analysis:
            market_section = analysis.split('## MARKET RISK ANALYSIS')[1].split('##')[0].strip()
            initial['market_risk_analysis'] = market_section
        
        # Credit Recommendation
        if '## CREDIT RECOMMENDATION' in analysis:
            rec_section = analysis.split('## CREDIT RECOMMENDATION')[1].split('##')[0].strip()
            initial['credit_recommendation'] = rec_section
        
        # Asset Quality
        if '## ASSET QUALITY' in analysis:
            asset_section = analysis.split('## ASSET QUALITY')[1].split('##')[0].strip()
            initial['asset_quality'] = asset_section
        
        # Profitability
        if '## PROFITABILITY' in analysis:
            prof_section = analysis.split('## PROFITABILITY')[1].split('##')[0].strip()
            initial['profitability_analysis'] = prof_section
        
        # Funding & Liquidity
        if '## FUNDING & LIQUIDITY' in analysis:
            funding_section = analysis.split('## FUNDING & LIQUIDITY')[1].split('##', 1)[0].strip()
            initial['funding_liquidity'] = funding_section
            
        return initial

    def form_valid(self, form):
        form.instance.is_draft = 'save_draft' in self.request.POST
        
        # Compile all the form data into a structured analysis
        analysis_content = self._compile_analysis_content(form)
        form.instance.analysis = analysis_content
        
        # If not a draft, set completion timestamp
        if not form.instance.is_draft:
            form.instance.completed_at = timezone.now()
        
        response = super().form_valid(form)
        # --- Workflow Transition ---
        if not form.instance.is_draft:
            try:
                from workflow.models import WorkflowStateTransition
                from workflow.services import WorkflowEngine
                credit_request = form.instance.credit_request
                print(f"DEBUG: Attempting workflow transition for CreditRequest {credit_request.pk}")
                print(f"DEBUG: Current workflow state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                transition = WorkflowStateTransition.objects.filter(
                    from_state=credit_request.workflow_state,
                    name__iexact="Complete Credit Questionnaire"
                ).first()
                print(f"DEBUG: Transition query result: {transition}")
                if transition:
                    print(f"DEBUG: Transition found. To state: {transition.to_state} (ID: {transition.to_state_id})")
                    WorkflowEngine.transition_request(
                        credit_request=credit_request,
                        to_state=transition.to_state,
                        user=self.request.user,
                        action_name=transition.name
                    )
                    print(f"DEBUG: Workflow transition successful. New state: {credit_request.workflow_state} (ID: {credit_request.workflow_state_id})")
                else:
                    print("WARNING: No valid workflow transition found for completing questionnaire.")
            except Exception as e:
                print(f"ERROR: Failed to transition workflow state after questionnaire submit: {e}")
        return response
    
    def _compile_analysis_content(self, form):
        # Same as in CreateView
        sections = [
            {'title': 'EXECUTIVE SUMMARY', 'content': [
                {'subtitle': 'Purpose of Application', 'text': form.cleaned_data.get('purpose_of_application', '')},
            ]},
            {'title': 'FINANCIAL SUMMARY', 'content': [
                {'subtitle': 'Rating: ' + form.cleaned_data.get('current_rating', ''), 'text': form.cleaned_data.get('financial_summary', '')},
                {'subtitle': 'Rating Outlook', 'text': form.cleaned_data.get('rating_outlook', '')},
            ]},
            {'title': 'KEY RISKS', 'content': [
                {'text': form.cleaned_data.get('key_risks', '')},
            ]},
            {'title': 'MARKET RISK ANALYSIS', 'content': [
                {'text': form.cleaned_data.get('market_risk_analysis', '')},
            ]},
            {'title': 'CREDIT RECOMMENDATION', 'content': [
                {'text': form.cleaned_data.get('credit_recommendation', '')},
            ]},
            {'title': 'ASSET QUALITY', 'content': [
                {'text': form.cleaned_data.get('asset_quality', '')},
            ]},
            {'title': 'PROFITABILITY', 'content': [
                {'text': form.cleaned_data.get('profitability_analysis', '')},
            ]},
            {'title': 'FUNDING & LIQUIDITY', 'content': [
                {'text': form.cleaned_data.get('funding_liquidity', '')},
            ]},
        ]
        
        # Format the content as markdown
        analysis = ''
        for section in sections:
            analysis += f"## {section['title']}\n\n"
            for item in section['content']:
                if 'subtitle' in item:
                    analysis += f"### {item['subtitle']}\n"
                analysis += f"{item['text']}\n\n"
        
        return analysis
    
    def get_success_url(self):
        if self.object.is_draft:
            messages.success(self.request, 'Credit Analysis updated and saved as draft.')
        else:
            messages.success(self.request, 'Credit Analysis updated and submitted successfully.')
        return reverse_lazy('creditrequest_detail', kwargs={'pk': self.object.credit_request.pk})

class CreditAnalysisDetailView(LoginRequiredMixin, DetailView):
    model = CreditAnalysis
    template_name = 'credit_workflow/creditanalysis_detail.html'
    context_object_name = 'analysis'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the credit request for additional context
        context['credit_request'] = self.object.credit_request
        return context

# Create a new AssignedRequestsView class
class AssignedRequestsView(LoginRequiredMixin, ListView):
    """View for requests assigned to the current user based on their role."""
    model = CreditRequest
    template_name = 'credit_workflow/assigned_requests.html'
    context_object_name = 'assigned_requests'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        
        # Determine the queryset based on the user's role
        if hasattr(user, 'role'):
            role = getattr(user, 'role', None)
            
            if role == 'RELATIONSHIP_MANAGER':
                # Relationship managers see their submitted requests
                queryset = CreditRequest.objects.filter(submitter=user)
            elif role == 'CREDIT_ANALYST':
                # Credit analysts see requests assigned to them
                queryset = CreditRequest.objects.filter(assigned_analyst=user)
            elif role == 'BUSINESS_SPONSOR':
                # Business sponsors see requests where they are the sponsor
                queryset = CreditRequest.objects.filter(business_sponsor=user)
            elif role == 'LEGAL_REVIEWER':
                # Legal reviewers see requests in legal review
                try:
                    legal_review_states = WorkflowState.objects.filter(
                        name__in=['LEGAL_REVIEW_IN_PROGRESS', 'LEGAL_REVIEW_DRAFT'])
                    queryset = CreditRequest.objects.filter(workflow_state__in=legal_review_states)
                except:
                    queryset = CreditRequest.objects.none()
            else:
                queryset = CreditRequest.objects.none()
        else:
            queryset = CreditRequest.objects.none()
        
        # Apply ordering
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = getattr(self.request.user, 'role', 'Unknown')
        return context
