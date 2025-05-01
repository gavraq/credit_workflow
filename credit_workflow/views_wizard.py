from django.urls import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from formtools.wizard.views import SessionWizardView
from django.forms import formset_factory
import json
from decimal import Decimal
from django.contrib import messages
from django.utils.crypto import get_random_string

# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)  # Convert Decimal to string
        return super().default(obj)

from .forms_wizard import (
    CreditRequestStep1Form, CreditRequestStep3Form, CreditRequestStep4Form
)
from .forms import CreditLimitForm
from .models import CreditRequest, CreditLimit

# Create basic formset for CreditLimit
CreditLimitBaseFormSet = formset_factory(
    CreditLimitForm,
    extra=1,
    can_delete=True,
)

# Define the form list for the wizard
FORMS = [
    ("step1", CreditRequestStep1Form),
    ("step2", CreditLimitBaseFormSet),  # Use the actual formset class, not a string
    ("step3", CreditRequestStep3Form),
    ("step4", CreditRequestStep4Form),
]

# Define templates for each step
TEMPLATES = {
    "step1": "credit_workflow/credit_request_step1.html",
    "step2": "credit_workflow/credit_request_step2.html",
    "step3": "credit_workflow/credit_request_step3.html",
    "step4": "credit_workflow/credit_request_step4.html",
}

class CreditRequestWizard(SessionWizardView):
    form_list = FORMS
    template_name = "credit_workflow/credit_request_step1.html"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # List to store limit requests in session
        self.limit_requests = []
        self.instance = None
    
    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]
    
    def get_form_instance(self, step):
        """Get or create the instance for the form."""
        if not hasattr(self, 'instance') or self.instance is None:
            # Check if we have a credit request ID in the URL
            credit_request_id = self.kwargs.get('pk')
            if credit_request_id:
                try:
                    self.instance = CreditRequest.objects.get(pk=credit_request_id)
                except CreditRequest.DoesNotExist:
                    self.instance = CreditRequest()
            else:
                self.instance = CreditRequest()
        return self.instance
    
    def get_form(self, step=None, data=None, files=None):
        """Override to add initial data for the formset in step 2"""
        step = step or self.steps.current
        
        # Special handling for step2 (credit limits)
        if step == 'step2':
            # Get stored limit requests from storage, or initialize empty list
            stored_data = self.storage.get_step_data('step2')
            
            if stored_data and 'limit_requests' in stored_data:
                try:
                    # Try to load stored limit requests
                    self.limit_requests = json.loads(stored_data['limit_requests'])
                except (json.JSONDecodeError, TypeError):
                    # If there's an error, start with empty list
                    self.limit_requests = []
            
            # Load existing credit limits if editing an existing CreditRequest
            if hasattr(self, 'instance') and self.instance and self.instance.pk:
                if not self.limit_requests:  # Only load from DB if we don't have any in session
                    limits = self.instance.limits.all()
                    for limit in limits:
                        self.limit_requests.append({
                            'limit_type': limit.limit_type_id,
                            'existing_limit_amount': str(limit.existing_limit_amount) if limit.existing_limit_amount else None,
                            'existing_tenor_months': limit.existing_tenor_months,
                            'proposed_limit_amount': str(limit.proposed_limit_amount),
                            'proposed_tenor_months': limit.proposed_tenor_months,
                        })
            
            # Get the form normally
            form = super().get_form(step, data, files)
            
            # Add the limit_requests to the context data
            self.limit_requests_context = self.limit_requests
            
            return form
        
        # For other steps, use default handling
        return super().get_form(step, data, files)
    
    def post(self, *args, **kwargs):
        """Handle the POST request, particularly the 'Add Limit Request' button"""
        current_step = self.steps.current
        
        # Check if we're going to a previous step using wizard_goto_step
        wizard_goto_step = self.request.POST.get('wizard_goto_step', None)
        if wizard_goto_step and wizard_goto_step in self.get_form_list():
            # If we're on step2, save the limit_requests data before going back
            if current_step == 'step2' and 'limit_requests' in self.request.POST:
                # Get the limit requests from the hidden field
                limit_requests_json = self.request.POST.get('limit_requests', '[]')
                try:
                    # Store the limit requests in the wizard storage
                    form_dict = {'limit_requests': limit_requests_json}
                    self.storage.set_step_data(current_step, form_dict)
                except (json.JSONDecodeError, TypeError):
                    # If there's an error, just continue with default behavior
                    pass
        
        # Special handling for step2 when adding a limit request
        if current_step == 'step2' and 'add_limit' in self.request.POST:
            # Get form data from request
            form = self.get_form(
                data=self.request.POST,
                files=self.request.FILES
            )
            
            # Extract the data from the form
            if form.is_valid():
                # Get the form that's being filled out (exclude empty forms)
                for form_data in form.cleaned_data:
                    # Skip empty forms and deleted forms
                    if not form_data or form_data.get('DELETE', False):
                        continue
                    
                    # If we have a limit type and amounts, add to our list
                    if form_data.get('limit_type') and form_data.get('proposed_limit_amount'):
                        # Convert limit_type to ID if it's a model instance
                        if hasattr(form_data['limit_type'], 'id'):
                            # Create a new dict with the ID instead of the model instance
                            cleaned_data = {k: v for k, v in form_data.items()}
                            cleaned_data['limit_type'] = form_data['limit_type'].id
                            self.limit_requests.append(cleaned_data)
                        else:
                            self.limit_requests.append(form_data)
            
            # Save the updated limit requests to storage
            form_dict = {'limit_requests': json.dumps(self.limit_requests, cls=DecimalEncoder)}
            self.storage.set_step_data(current_step, form_dict)
            
            # Instead of redirecting, create a new clean form and render the template
            form = self.get_form(current_step)
            context = self.get_context_data(form=form)
            return self.render(context)
        
        # Default form processing for other actions
        return super().post(*args, **kwargs)
    
    def process_step(self, form):
        """Process the current step before moving to the next"""
        step = self.steps.current
        
        # Special handling for step2 (credit limits)
        if step == 'step2':
            # Handle normal form processing first
            result = super().process_step(form)
            
            # Check if we have limit_requests in the POST data (from the hidden field)
            if 'limit_requests' in self.request.POST:
                # Create a dictionary with our limit_requests from the hidden field
                form_dict = result.copy()
                form_dict['limit_requests'] = self.request.POST['limit_requests']
                return form_dict
            # Then store our special limit_requests data (legacy approach)
            elif hasattr(self, 'limit_requests'):
                # Create a dictionary with our limit_requests
                form_dict = result.copy()
                form_dict['limit_requests'] = json.dumps(self.limit_requests, cls=DecimalEncoder)
                return form_dict
            
            # If we don't have limit_requests, return normal result
            return result
        
        # For other steps, use default handling
        return super().process_step(form)
    
    def get_context_data(self, form, **kwargs):
        """Add additional context data for the template"""
        context = super().get_context_data(form=form, **kwargs)
        
        # Add mode (create/edit) to context
        if hasattr(self, 'instance') and self.instance and self.instance.pk:
            context['mode'] = 'edit'
            context['credit_request'] = self.instance
        else:
            context['mode'] = 'create'
        
        # For step2, add the current limit requests to the context
        if self.steps.current == 'step2':
            if hasattr(self, 'limit_requests'):
                context['limit_requests'] = self.limit_requests
            else:
                context['limit_requests'] = []
            
            # Add available limit types to the context
            from .models import LimitType
            limit_types = LimitType.objects.all().order_by('name')
            context['limit_types'] = limit_types
        
        return context
    
    def get_form_initial(self, step):
        """Provide initial data for each step."""
        initial = self.initial_dict.get(step, {})
        
        # If we're editing an existing credit request, pre-populate form fields
        if hasattr(self, 'instance') and self.instance and self.instance.pk:
            if step == 'step1':
                for field in CreditRequestStep1Form.Meta.fields:
                    if hasattr(self.instance, field):
                        initial[field] = getattr(self.instance, field)
            
            elif step == 'step3':
                for field in CreditRequestStep3Form.Meta.fields:
                    if hasattr(self.instance, field):
                        initial[field] = getattr(self.instance, field)
            
            elif step == 'step4':
                for field in CreditRequestStep4Form.Meta.fields:
                    if hasattr(self.instance, field):
                        initial[field] = getattr(self.instance, field)
        
        return initial
    
    def done(self, form_list, **kwargs):
        """Final processing when the wizard is completed"""
        # Convert form_list to a dictionary keyed by step name for easier access
        forms_by_step = {}
        for step_name, form in zip(self.steps.all, form_list):
            forms_by_step[step_name] = form
        
        # Determine if we're creating a new record or updating existing
        is_new = not (hasattr(self, 'instance') and self.instance and self.instance.pk)
        
        # Create and save the CreditRequest from step1
        if is_new:
            credit_request = forms_by_step['step1'].save(commit=False)
        else:
            credit_request = self.instance
            # Update Step 1 fields
            for field, value in forms_by_step['step1'].cleaned_data.items():
                setattr(credit_request, field, value)
        
        # Apply data from steps 3 and 4
        for form in [forms_by_step['step3'], forms_by_step['step4']]:
            for field, value in form.cleaned_data.items():
                setattr(credit_request, field, value)
        
        # Set required fields
        from workflow.models import WorkflowState
        from datetime import datetime
        
        # Get the save action (draft, submit, or review)
        save_action = self.request.POST.get('save_action', 'draft')
        
        # Set workflow state based on the action
        if is_new or save_action == 'draft':
            try:
                credit_request.workflow_state = WorkflowState.objects.get(name__iexact='DRAFT')
            except WorkflowState.DoesNotExist:
                # Fallback to first workflow state if 'DRAFT' doesn't exist
                credit_request.workflow_state = WorkflowState.objects.first()
        elif save_action == 'submit':
            try:
                # Transition to SUBMITTED state
                credit_request.workflow_state = WorkflowState.objects.get(name__iexact='SUBMITTED')
                # Set submitted_at timestamp when transitioning to SUBMITTED
                from django.utils import timezone
                credit_request.submitted_at = timezone.now()
            except WorkflowState.DoesNotExist:
                # Fallback to DRAFT if SUBMITTED doesn't exist
                credit_request.workflow_state = WorkflowState.objects.get(name__iexact='DRAFT')
        elif save_action == 'review':
            try:
                # Transition to CREDIT_REVIEW state
                credit_request.workflow_state = WorkflowState.objects.get(name__iexact='CREDIT_REVIEW')
                # Set submitted_at timestamp when transitioning to CREDIT_REVIEW
                from django.utils import timezone
                credit_request.submitted_at = timezone.now()
            except WorkflowState.DoesNotExist:
                # Fallback to SUBMITTED if CREDIT_REVIEW doesn't exist
                try:
                    credit_request.workflow_state = WorkflowState.objects.get(name__iexact='SUBMITTED')
                except WorkflowState.DoesNotExist:
                    # Final fallback to DRAFT
                    credit_request.workflow_state = WorkflowState.objects.get(name__iexact='DRAFT')
        
        # Set submitter and submission time if new
        if is_new:
            credit_request.submitter = self.request.user
            from django.utils import timezone
            credit_request.submitted_at = timezone.now()
        
        # Auto-generate a unique request_number if not set and this is a new record
        if is_new and not credit_request.request_number:
            from django.utils import timezone
            base = timezone.now().strftime("CR%Y%m%d")
            for _ in range(10):
                candidate = f"{base}-{get_random_string(4).upper()}"
                if not type(credit_request).objects.filter(request_number=candidate).exists():
                    credit_request.request_number = candidate
                    break
            else:
                raise Exception("Could not generate unique request number")
        
        credit_request.save()
        
        # Handle credit limits
        # If we're updating, first delete existing limits that will be replaced
        if not is_new:
            credit_request.limits.all().delete()
        
        # Get the stored limit requests
        if hasattr(self, 'limit_requests') and self.limit_requests:
            # Save all the limit requests
            for limit_data in self.limit_requests:
                # Create a new CreditLimit object
                try:
                    # For existing limit_type values stored as IDs
                    if isinstance(limit_data.get('limit_type'), int) or str(limit_data.get('limit_type')).isdigit():
                        limit_type_id = int(limit_data.get('limit_type'))
                        limit = CreditLimit(
                            credit_request=credit_request,
                            limit_type_id=limit_type_id,
                            existing_limit_amount=limit_data.get('existing_limit_amount'),
                            existing_tenor_months=limit_data.get('existing_tenor_months'),
                            proposed_limit_amount=limit_data.get('proposed_limit_amount'),
                            proposed_tenor_months=limit_data.get('proposed_tenor_months')
                        )
                    # For old data that might store it as a string code
                    else:
                        # We have string data in storage - try to find the LimitType
                        from .models import LimitType
                        limit_type_code = limit_data.get('limit_type')
                        limit_type = LimitType.objects.filter(code=limit_type_code).first()
                        if not limit_type:
                            # If not found by code, try to find by name
                            limit_type = LimitType.objects.filter(name=limit_type_code).first()
                        if not limit_type:
                            # Create a new one as fallback
                            limit_type = LimitType.objects.create(code=limit_type_code, name=limit_type_code)
                        
                        limit = CreditLimit(
                            credit_request=credit_request,
                            limit_type=limit_type,
                            existing_limit_amount=limit_data.get('existing_limit_amount'),
                            existing_tenor_months=limit_data.get('existing_tenor_months'),
                            proposed_limit_amount=limit_data.get('proposed_limit_amount'),
                            proposed_tenor_months=limit_data.get('proposed_tenor_months')
                        )
                    
                    limit.save()
                except Exception as e:
                    # Log the error but continue processing other limit requests
                    print(f"Error saving limit: {e}")
        
        # Also check for the form data from step2 which might have limit_requests as JSON string
        step2_data = self.storage.get_step_data('step2')
        if step2_data and 'limit_requests' in step2_data and not self.limit_requests:
            try:
                # Parse the JSON string
                limit_requests_data = json.loads(step2_data['limit_requests'])
                
                # Process each limit request
                for limit_data in limit_requests_data:
                    # Skip if we don't have required data
                    if not limit_data.get('limit_type') or not limit_data.get('proposed_limit_amount'):
                        continue
                    
                    # Create the CreditLimit object
                    limit = CreditLimit(
                        credit_request=credit_request,
                        limit_type_id=int(limit_data.get('limit_type')),
                        existing_limit_amount=limit_data.get('existing_limit_amount'),
                        existing_tenor_months=limit_data.get('existing_tenor_months'),
                        proposed_limit_amount=limit_data.get('proposed_limit_amount'),
                        proposed_tenor_months=limit_data.get('proposed_tenor_months')
                    )
                    limit.save()
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                # Log the error but continue processing
                print(f"Error processing JSON limit requests: {e}")
        
        # Set success message based on the action
        if save_action == 'draft':
            if is_new:
                messages.success(self.request, f'Credit request {credit_request.request_number} saved as draft successfully.')
            else:
                messages.success(self.request, f'Credit request {credit_request.request_number} updated and saved as draft successfully.')
        elif save_action == 'submit':
            messages.success(self.request, f'Credit request {credit_request.request_number} submitted successfully and is now in the {credit_request.workflow_state.name} state.')
        elif save_action == 'review':
            messages.success(self.request, f'Credit request {credit_request.request_number} sent for review and is now in the {credit_request.workflow_state.name} state.')
        
        # Redirect to detail view
        return redirect('creditrequest_detail', pk=credit_request.pk)
