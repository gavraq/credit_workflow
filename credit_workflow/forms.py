from django import forms
from .models import CreditRequest, CreditLimit, CounterParty, CreditQuestionnaire, LegalReview, Document, NotificationPreference, LimitType, CreditAnalysis
from django.core.exceptions import ValidationError

class BaseForm(forms.ModelForm):
    """
    Base form with common widgets, error styling, and validation helpers.
    """
    def add_error_message(self, field, message):
        self.add_error(field, message)

from django import forms
from .models import CounterParty

class CreditRequestForm(BaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add data-cif attribute to each counterparty option
        counterparty_field = self.fields.get('counterparty')
        if counterparty_field is not None:
            queryset = counterparty_field.queryset
            choices = []
            for obj in queryset:
                choices.append((obj.pk, obj.name))  # keep label for now
            self.fields['counterparty'].choices = choices
            self.counterparty_cif_map = {str(obj.pk): obj.cif_number for obj in queryset}
        # Remove blank/empty choice for priority
        if 'priority' in self.fields:
            self.fields['priority'].choices = [c for c in self.fields['priority'].choices if c[0]]
            self.fields['priority'].required = True
    class Meta:
        model = CreditRequest
        fields = [
            # Header & workflow
            'request_number', 'counterparty', 'guarantor', 'submitter',
            # Assignment & sponsors
            'business_sponsor', 'second_sponsor',
            # Prioritisation
            'priority', 'required_by_date', 'priority_justification',
            # Revenue & risk
            'revenue_last_12m', 'projected_revenue', 'projected_rorwa_percentage', 'country_risk_limit_confirmed',
            # Comments & relationship
            'client_introduction_details', 'kyc_approval_status', 'senior_client_contact', 'last_client_visit_date',
            # Legal/financial
            'has_legal_opinion', 'financial_statements_received', 'interim_financials_info',
        ]
        widgets = {
            'counterparty': forms.Select(attrs={'class': 'form-control'}),
            'guarantor': forms.Select(attrs={'class': 'form-control'}),
            'request_number': forms.TextInput(attrs={'class': 'form-control'}),
            'submitter': forms.Select(attrs={'class': 'form-control'}),
            'business_sponsor': forms.Select(attrs={'class': 'form-control'}),
            'second_sponsor': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'required_by_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'priority_justification': forms.Textarea(attrs={'class': 'form-control'}),
            'revenue_last_12m': forms.NumberInput(attrs={'class': 'form-control'}),
            'projected_revenue': forms.NumberInput(attrs={'class': 'form-control'}),
            'projected_rorwa_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'country_risk_limit_confirmed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'client_introduction_details': forms.Textarea(attrs={'class': 'form-control'}),
            'kyc_approval_status': forms.Select(attrs={'class': 'form-control'}),
            'senior_client_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'last_client_visit_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'has_legal_opinion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'financial_statements_received': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'interim_financials_info': forms.Textarea(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('priority') == 'High' and not cleaned.get('priority_justification'):
            self.add_error('priority_justification', 'Justification is required for high priority requests.')
        return cleaned

    # For multi-step UI, you can later split fields by logical section.
    # For draft support, handle in the view (not form) via workflow_state or is_draft.


class CreditLimitForm(BaseForm):
    class Meta:
        model = CreditLimit
        fields = [
            'limit_type',
            'existing_limit_amount',
            'existing_tenor_months',
            'proposed_limit_amount',
            'proposed_tenor_months',
            'credit_request',
        ]
        widgets = {
            'limit_type': forms.Select(attrs={'class': 'form-select form-control'}),
            'existing_limit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'existing_tenor_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'proposed_limit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'proposed_tenor_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'credit_request': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The credit_request field will be set in the view when saving
        self.fields['credit_request'].required = False
        # Set the queryset for limit_type to show all available limit types
        self.fields['limit_type'].queryset = LimitType.objects.all().order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        # Ensure proposed limit amount and tenor are provided
        if not cleaned_data.get('proposed_limit_amount'):
            self.add_error('proposed_limit_amount', 'This field is required')
        if not cleaned_data.get('proposed_tenor_months'):
            self.add_error('proposed_tenor_months', 'This field is required')
        if not cleaned_data.get('limit_type'):
            self.add_error('limit_type', 'This field is required')
        return cleaned_data

class CounterPartyForm(BaseForm):
    class Meta:
        model = CounterParty
        fields = [
            'name',
            'cif_number',
            'country_of_risk',
            'business_description',
            'has_guarantor',
            'guarantor_details',
            'rating_current',
            'rating_previous',
            'sp_rating',
            'moodys_rating',
            'fitch_rating',
        ]

class CreditReviewForm(BaseForm):
    class Meta:
        model = CreditRequest
        fields = [
            'assigned_analyst',
            'questionnaire_required',
            'da_level',
            'credit_review_notes',
        ]
        widgets = {
            'credit_review_notes': forms.Textarea(attrs={'rows': 3}),
        }

class CreditQuestionnaireForm(BaseForm):
    class Meta:
        model = CreditQuestionnaire
        fields = [
            'credit_request',
            'author',
            'content',
            'is_draft',
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Enter questionnaire answers...'}),
        }

class LegalReviewForm(BaseForm):
    class Meta:
        model = LegalReview
        fields = [
            'credit_request',
            'reviewer',
            'comments',
            'is_draft',
        ]
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Enter legal review comments...'}),
        }

class DocumentForm(BaseForm):
    class Meta:
        model = Document
        fields = ['credit_request', 'file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class NotificationPreferenceForm(BaseForm):
    class Meta:
        model = NotificationPreference
        fields = ['type', 'enabled']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CreditAnalysisForm(BaseForm):
    """Form for Credit Analysis based on the screenshots provided."""
    RATING_CHOICES = [
        ('RG20', 'RG20'),
        ('RG21', 'RG21'),
        ('RG22', 'RG22'),
        ('RG23', 'RG23'),
        ('RG24', 'RG24'),
        ('RG25', 'RG25'),
        ('RG26', 'RG26'),
    ]
    
    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('GBP', 'GBP'),
        ('GHS', 'GHS'),
    ]
    
    # Executive Summary Fields
    purpose_of_application = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False
    )
    
    # Financial Summary Fields
    financial_summary = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False
    )
    
    # Rating and Outlook
    current_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    rating_outlook = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    # Key Risks
    key_risks = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False
    )
    
    # Market Risk Sensitivities
    market_risk_analysis = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False
    )
    
    # Credit Recommendation
    credit_recommendation = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False
    )
    
    # Asset Quality
    asset_quality = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False
    )
    
    # Profitability Analysis
    profitability_analysis = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False
    )
    
    # Funding & Liquidity
    funding_liquidity = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = CreditAnalysis
        fields = [
            'credit_request',
            'analyst',
            'analysis',
            'is_draft',
        ]
        widgets = {
            'credit_request': forms.Select(attrs={'class': 'form-select'}),
            'analyst': forms.HiddenInput(),
            'analysis': forms.Textarea(attrs={'rows': 10, 'class': 'form-control d-none'}),
            'is_draft': forms.HiddenInput(),
        }
