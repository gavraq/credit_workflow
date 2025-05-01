from django import forms
from .models import CreditRequest, CreditLimit
from .forms import BaseForm
from users.models import User

# Step 1: Basic Information
class CreditRequestStep1Form(BaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter priority choices
        if 'priority' in self.fields:
            self.fields['priority'].choices = [c for c in self.fields['priority'].choices if c[0]]
            self.fields['priority'].required = True
            
        # Add counterparty customization (from standard form)
        counterparty_field = self.fields.get('counterparty')
        if counterparty_field is not None:
            queryset = counterparty_field.queryset
            choices = []
            for obj in queryset:
                choices.append((obj.pk, obj.name))
            self.fields['counterparty'].choices = choices
            self.counterparty_cif_map = {str(obj.pk): obj.cif_number for obj in queryset}
    
    def clean(self):
        cleaned = super().clean()
        if cleaned.get('priority') == 'High' and not cleaned.get('priority_justification'):
            self.add_error('priority_justification', 'Justification is required for high priority requests.')
        return cleaned
    
    class Meta:
        model = CreditRequest
        fields = [
            'counterparty', 'guarantor', 'title', 'priority', 
            'required_by_date', 'priority_justification'
        ]
        widgets = {
            'counterparty': forms.Select(attrs={'class': 'form-select'}),
            'guarantor': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter a descriptive title'}),
            'priority': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'required_by_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'priority_justification': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 
                                                           'placeholder': 'Explain why this request has high priority'})
        }

# Step 2: Limit Requests (handled via formset in the view/template)

# Step 3: Relationship Information
class CreditRequestStep3Form(BaseForm):
    KYC_STATUS_CHOICES = [
        ('Approved', 'Approved'),
        ('Pending', 'Pending'),
        ('Not Approved', 'Not Approved'),
        ('Not Required', 'Not Required'),
    ]
    
    kyc_approval_status = forms.ChoiceField(
        choices=KYC_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If we have an instance, set the kyc_approval_status value from the instance
        if self.instance and hasattr(self.instance, 'kyc_approval_status') and self.instance.kyc_approval_status:
            # If the status isn't in our choices, add it
            existing_status = self.instance.kyc_approval_status
            choices = dict(self.KYC_STATUS_CHOICES)
            if existing_status not in choices:
                self.fields['kyc_approval_status'].choices += [(existing_status, existing_status)]
    
    class Meta:
        model = CreditRequest
        fields = [
            'client_introduction_details', 'kyc_approval_status', 'senior_client_contact', 'last_client_visit_date',
            'revenue_last_12m', 'projected_revenue', 'projected_rorwa_percentage',
            'has_legal_opinion', 'financial_statements_received', 'interim_financials_info'
        ]
        widgets = {
            'client_introduction_details': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 
                                                          'placeholder': 'Provide a brief introduction to the client and their business.'}),
            'senior_client_contact': forms.TextInput(attrs={'class': 'form-control', 
                                                     'placeholder': 'Name and position of senior client contact'}),
            'last_client_visit_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'revenue_last_12m': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'projected_revenue': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'projected_rorwa_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'has_legal_opinion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'financial_statements_received': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'interim_financials_info': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 
                                                     'placeholder': 'Please provide details about interim financial statements'}),
        }

# Step 4: Business Justification
class CreditRequestStep4Form(BaseForm):  # Changed to inherit from BaseForm for consistency
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter business sponsors to only show users with that role
        business_sponsors = User.objects.filter(role=User.Role.BUSINESS_SPONSOR)
        
        # Set the queryset for the business_sponsor field
        self.fields['business_sponsor'].queryset = business_sponsors
        
        # Override the label_from_instance to display full name
        self.fields['business_sponsor'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name}"
        
        # Also filter second_sponsor if available
        if 'second_sponsor' in self.fields:
            # Allow any user to be a second sponsor
            all_users = User.objects.all()
            self.fields['second_sponsor'].queryset = all_users
            self.fields['second_sponsor'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name}"
    
    class Meta:
        model = CreditRequest
        fields = [
            'description', 'country_risk_limit_confirmed', 'business_sponsor', 'second_sponsor'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 
                                               'placeholder': 'Describe the business purpose of this credit request'}),
            'country_risk_limit_confirmed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'business_sponsor': forms.Select(attrs={'class': 'form-select'}),
            'second_sponsor': forms.Select(attrs={'class': 'form-select'}),
        }
