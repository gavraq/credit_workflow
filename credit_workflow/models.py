from django.db import models
from workflow.models import WorkflowState
from django.contrib.auth import get_user_model
User = get_user_model()

class LimitType(models.Model):
    """A type of credit limit that can be requested."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class CounterParty(models.Model):
    """
    Represents a counterparty entity for which a credit request may be submitted.
    """
    name = models.CharField(max_length=200)
    cif_number = models.CharField(max_length=50, unique=True)
    country_of_risk = models.CharField(max_length=100)
    business_description = models.TextField(blank=True, null=True)
    has_guarantor = models.BooleanField(default=False)
    guarantor_details = models.TextField(blank=True, null=True)
    rating_current = models.CharField(max_length=10, blank=True, null=True)
    rating_previous = models.CharField(max_length=10, blank=True, null=True)
    sp_rating = models.CharField(max_length=10, blank=True, null=True)
    moodys_rating = models.CharField(max_length=10, blank=True, null=True)
    fitch_rating = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Counterparty"
        verbose_name_plural = "Counterparties"

    def __str__(self):
        return f"{self.name} ({self.cif_number})"

class CreditRequest(models.Model):
    """
    Represents a credit limit request in the workflow system.
    """
    PRIORITY_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
    ]
    request_number = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    counterparty = models.ForeignKey(CounterParty, on_delete=models.CASCADE)
    guarantor = models.ForeignKey(CounterParty, on_delete=models.SET_NULL, null=True, blank=True, related_name='guaranteed_requests')  # Optional
    workflow_state = models.ForeignKey(WorkflowState, on_delete=models.PROTECT)
    submitter = models.ForeignKey(User, related_name="submitted_requests", on_delete=models.PROTECT)
    assigned_analyst = models.ForeignKey(User, related_name="assigned_analyses", on_delete=models.SET_NULL, null=True, blank=True)
    business_sponsor = models.ForeignKey(User, related_name="business_sponsored_requests", on_delete=models.PROTECT)
    second_sponsor = models.ForeignKey(User, related_name="second_sponsored_requests", on_delete=models.SET_NULL, null=True, blank=True)
    da_level = models.PositiveSmallIntegerField(null=True, blank=True)
    questionnaire_required = models.BooleanField(default=False)
    credit_review_notes = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=6, choices=PRIORITY_CHOICES)
    required_by_date = models.DateField()
    priority_justification = models.TextField(blank=True, null=True)
    revenue_last_12m = models.DecimalField(max_digits=15, decimal_places=2)
    projected_revenue = models.DecimalField(max_digits=15, decimal_places=2)
    projected_rorwa_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    country_risk_limit_confirmed = models.BooleanField(default=False)
    client_introduction_details = models.TextField()
    kyc_approval_status = models.CharField(max_length=50)
    senior_client_contact = models.CharField(max_length=100)
    last_client_visit_date = models.DateField()
    has_legal_opinion = models.BooleanField(default=False)
    financial_statements_received = models.BooleanField(default=False)
    interim_financials_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"CreditRequest {self.request_number} for {self.counterparty.name}"

class CreditQuestionnaire(models.Model):
    """
    Questionnaire completed as part of the credit request process.
    """
    credit_request = models.OneToOneField(CreditRequest, on_delete=models.CASCADE, related_name="questionnaire")
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    content = models.TextField()
    is_draft = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Questionnaire for {self.credit_request}"
    
    def _extract_section_content(self, section_title, field_title=None):
        """
        Extract content from a specific section and optionally a specific field within that section.
        Handles various markdown and text formatting styles.
        """
        import re
        
        if not self.content:
            return ""
        
        # Debug logging
        print(f"DEBUG - Extracting section: '{section_title}' field: '{field_title}'")
        
        # Clean up section title for matching
        clean_section_title = section_title.lstrip('#').strip()
        
        # Try multiple patterns for section headers
        section_patterns = [
            # Standard pattern with ## and two newlines
            rf"## {re.escape(clean_section_title)}\s*\n\n([\s\S]*?)(?=\n## |$)",
            # Alternative pattern with just one newline after the heading
            rf"## {re.escape(clean_section_title)}\s*\n([\s\S]*?)(?=\n## |$)",
            # Pattern without the ## markdown (just the heading text with two newlines)
            rf"{re.escape(clean_section_title)}\s*\n\n([\s\S]*?)(?=\n[A-Z][A-Z\s]+|$)",
            # Pattern without the ## markdown and only one newline
            rf"{re.escape(clean_section_title)}\s*\n([\s\S]*?)(?=\n[A-Z][A-Z\s]+|$)",
            # Very flexible pattern that just looks for the section title
            rf"(?:##\s*)?{re.escape(clean_section_title)}[^\n]*\n([\s\S]*?)(?=\n(?:##\s*)?[A-Z][A-Z\s\']+|$)"
        ]
        
        section_content = ""
        matched_pattern = ""
        
        # Try each pattern until we find a match
        for pattern in section_patterns:
            section_match = re.search(pattern, self.content)
            if section_match:
                section_content = section_match.group(1).strip()
                matched_pattern = pattern[:30] + "..."
                print(f"DEBUG - Found section content with pattern: {matched_pattern}")
                print(f"DEBUG - Section content length: {len(section_content)}")
                break
        
        if not section_content:
            print(f"DEBUG - Could not find section: {section_title}")
            return ""
        
        # If no specific field is requested, return the entire section
        if not field_title:
            return section_content
        
        # Clean up field title for matching
        clean_field_title = field_title.lstrip('#').strip()
        
        # Find the specific field within the section by looking for the label
        # We need to escape special characters in the field title for regex
        escaped_field_title = re.escape(clean_field_title)
        
        # Try multiple patterns for field headers
        field_patterns = [
            # Standard pattern with ### and newline
            rf"### {escaped_field_title}\s*\n([\s\S]*?)(?=\n### |\n\n|$)",
            # Alternative pattern with ## and newline
            rf"## {escaped_field_title}\s*\n([\s\S]*?)(?=\n## |\n\n|$)",
            # Alternative pattern without markdown but with colon
            rf"{escaped_field_title}:\s*\n([\s\S]*?)(?=\n[A-Za-z][^\n:]+:|\n\n|$)",
            # Very flexible pattern that looks for the field title followed by any content
            rf"(?:###\s*)?{escaped_field_title}[^\n]*\n([\s\S]*?)(?=\n(?:###\s*)?[A-Za-z]|$)"
        ]
        
        field_content = ""
        matched_field_pattern = ""
        
        # Try each pattern until we find a match
        for pattern in field_patterns:
            field_match = re.search(pattern, section_content)
            if field_match:
                field_content = field_match.group(1).strip()
                matched_field_pattern = pattern[:30] + "..."
                print(f"DEBUG - Found field content with pattern: {matched_field_pattern}")
                print(f"DEBUG - Field content length: {len(field_content)}")
                break
        
        if not field_content:
            # Try a more flexible match that looks for a field that contains our title
            print(f"DEBUG - Trying flexible field match for: {field_title}")
            for line in section_content.split('\n'):
                # Look for lines that might be field headers
                if ((line.startswith('### ') or line.startswith('## ')) and clean_field_title.lower() in line.lower()) or \
                   (': ' in line and clean_field_title.lower() in line.lower()):
                    # Found a matching field header, now extract its content
                    print(f"DEBUG - Found potential field header: {line}")
                    field_header = line
                    try:
                        field_header_index = section_content.index(field_header)
                        field_content_start = field_header_index + len(field_header) + 1  # +1 for newline
                        
                        # Find the end of this field (next field or end of section)
                        next_field_match = re.search(r'\n(?:###|##) ', section_content[field_content_start:])
                        if next_field_match:
                            field_content_end = field_content_start + next_field_match.start()
                            field_content = section_content[field_content_start:field_content_end].strip()
                        else:
                            field_content = section_content[field_content_start:].strip()
                        
                        print(f"DEBUG - Found field with flexible match: {field_header}")
                        print(f"DEBUG - Field content length: {len(field_content)}")
                        break
                    except Exception as e:
                        print(f"DEBUG - Error in flexible match: {str(e)}")
        
        if not field_content:
            print(f"DEBUG - Could not find field: {field_title}")
        
        return field_content
    
    @property
    def business_model_details(self):
        return self._extract_section_content("COUNTERPARTY'S BUSINESS MODEL", "Basic details of the counterparty business model (i.e. what do they do, how do they generate revenue?)")
    
    @property
    def key_suppliers_customers(self):
        return self._extract_section_content("COUNTERPARTY'S BUSINESS MODEL", "Key suppliers and/or customers; typical terms of trade or credit provided to customers?")
    
    @property
    def trading_activity_rationale(self):
        # Combine all fields in this section into one text
        # Try multiple variations of the section title
        section_titles = [
            "TRADING ACTIVITY / RATIONALE FOR LIMITS",
            "TRADING ACTIVITY/RATIONALE FOR LIMITS",
            "TRADING ACTIVITY RATIONALE FOR LIMITS",
            "TRADING ACTIVITY",
            "## TRADING ACTIVITY / RATIONALE FOR LIMITS",  # Include markdown format
            "##TRADING ACTIVITY / RATIONALE FOR LIMITS"    # Handle no space after ##
        ]
        
        section_content = ""
        for title in section_titles:
            section_content = self._extract_section_content(title)
            if section_content:
                break
                
        if not section_content:
            return ""
            
        # Extract all field values and combine them
        import re
        # Try to find fields with ### headers
        fields = re.findall(r'### ([^\n]+)\n([\s\S]*?)(?=\n### |\n\n|$)', section_content)
        
        # If that doesn't work, try without the ### format
        if not fields:
            fields = re.findall(r'([A-Za-z][^\n:]+):\s*\n([\s\S]*?)(?=\n[A-Za-z][^\n:]+:|$)', section_content)
        
        # If we found fields, format them nicely
        if fields:
            result = ""
            for field_title, field_content in fields:
                # Clean up the title (remove ###)
                clean_title = field_title.lstrip('#').strip()
                result += f"{clean_title}:\n{field_content.strip()}\n\n"
            return result
        else:
            # If no fields found, return the entire section content
            return section_content
    
    @property
    def trading_policy_governance(self):
        # Get the specific field we want from this section
        # Try multiple variations of the title
        section_titles = ["POLICIES AND GOVERNANCE", "POLICIES & GOVERNANCE", "POLICIES"]
        field_titles = ["Who determines trading / hedge policies (e.g. Board)?", "Who determines trading/hedge policies?", "Policy determination"]
        
        # Try each combination
        for section_title in section_titles:
            for field_title in field_titles:
                content = self._extract_section_content(section_title, field_title)
                if content:
                    return content
        
        # If no matches found, try getting the whole section
        for section_title in section_titles:
            content = self._extract_section_content(section_title)
            if content:
                return content
                
        return ""
    
    @property
    def liquidity_management(self):
        # Combine all fields in this section into one text
        # Try multiple variations of the section title
        section_titles = ["LIQUIDITY MANAGEMENT", "LIQUIDITY"]
        
        section_content = ""
        for title in section_titles:
            section_content = self._extract_section_content(title)
            if section_content:
                break
                
        if not section_content:
            return ""
            
        # Extract all field values and combine them
        import re
        fields = re.findall(r'### ([^\n]+)\n([\s\S]*?)(?=\n### |\n\n|$)', section_content)
        if not fields:
            return section_content
            
        result = ""
        for field_title, field_content in fields:
            result += f"{field_title}:\n{field_content.strip()}\n\n"
        return result

class LegalReview(models.Model):
    """
    Legal review for a credit request.
    """
    # Core relationship fields
    credit_request = models.OneToOneField(CreditRequest, on_delete=models.CASCADE, related_name="legal_review")
    reviewer = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # Master Agreement details
    ISDA_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
        ('pending', 'Pending')
    ]
    
    GOVERNING_LAW_CHOICES = [
        ('english', 'English'),
        ('new_york', 'New York'),
        ('other', 'Other')
    ]
    
    OPINION_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
        ('not_applicable', 'Not Applicable')
    ]
    
    CSA_CHOICES = [
        ('one_way', 'One-way'),
        ('two_way', 'Two-way'),
        ('none', 'None')
    ]
    
    # Master Agreement fields
    isda_master_agreement = models.CharField(max_length=10, choices=ISDA_CHOICES, default='no')
    governing_law = models.CharField(max_length=20, choices=GOVERNING_LAW_CHOICES, default='english')
    counterparty_termination_events = models.TextField(blank=True, null=True)
    counterparty_default_events = models.CharField(max_length=50, blank=True, null=True)
    grace_period = models.CharField(max_length=50, blank=True, null=True)
    material_provisions = models.TextField(blank=True, null=True)
    positive_netting_opinion = models.CharField(max_length=20, choices=OPINION_CHOICES, default='no')
    
    # Credit Support Annex fields
    credit_support_annex = models.CharField(max_length=10, choices=ISDA_CHOICES, default='no')
    csa_type = models.CharField(max_length=10, choices=CSA_CHOICES, blank=True, null=True)
    iosco_compliant = models.CharField(max_length=10, choices=ISDA_CHOICES, blank=True, null=True)
    csa_threshold = models.CharField(max_length=50, blank=True, null=True)
    csa_minimum_transfer = models.CharField(max_length=50, blank=True, null=True)
    csa_independent_amount = models.CharField(max_length=50, blank=True, null=True)
    positive_collateral_opinion = models.CharField(max_length=20, choices=OPINION_CHOICES, default='no')
    csa_additional_provisions = models.TextField(blank=True, null=True)
    
    # Original fields
    comments = models.TextField()
    is_draft = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"LegalReview for {self.credit_request}"

class CreditAnalysis(models.Model):
    """
    Credit analysis for a credit request.
    """
    credit_request = models.OneToOneField(CreditRequest, on_delete=models.CASCADE, related_name="credit_analysis")
    analyst = models.ForeignKey(User, on_delete=models.PROTECT)
    analysis = models.TextField()
    is_draft = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CreditAnalysis for {self.credit_request}"

class CreditLimit(models.Model):
    """
    Represents a credit limit (existing or proposed) for a credit request.
    """
    credit_request = models.ForeignKey(CreditRequest, on_delete=models.CASCADE, related_name="limits")
    limit_type = models.ForeignKey(LimitType, on_delete=models.PROTECT)  # Restored ForeignKey
    existing_limit_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    existing_tenor_months = models.PositiveIntegerField(null=True, blank=True)
    proposed_limit_amount = models.DecimalField(max_digits=15, decimal_places=2)
    proposed_tenor_months = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.limit_type} for {self.credit_request}"

class CreditPaper(models.Model):
    """
    Final compiled credit paper for a credit request.
    """
    credit_request = models.OneToOneField(CreditRequest, on_delete=models.CASCADE, related_name="credit_paper")
    compiled_by = models.ForeignKey(User, on_delete=models.PROTECT)
    content = models.TextField()
    is_draft = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CreditPaper for {self.credit_request}"

class Document(models.Model):
    """
    Document uploaded and attached to a CreditRequest.
    """
    credit_request = models.ForeignKey(CreditRequest, on_delete=models.CASCADE, related_name="credit_documents")
    file = models.FileField(upload_to="credit_documents/%Y/%m/%d/")
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="credit_uploaded_documents")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.credit_request} uploaded by {self.uploaded_by}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("workflow", "Workflow"),
        ("document", "Document"),
        ("reminder", "Reminder"),
        ("other", "Other"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="credit_notifications")
    type = models.CharField(max_length=32, choices=NOTIFICATION_TYPES)
    content = models.TextField()
    link = models.URLField(blank=True, null=True)
    read = models.BooleanField(default=False)
    dismissed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.user}: {self.content[:40]}"

class NotificationPreference(models.Model):
    NOTIFICATION_TYPES = Notification.NOTIFICATION_TYPES
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="credit_notification_preferences")
    type = models.CharField(max_length=32, choices=NOTIFICATION_TYPES)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "type")

    def __str__(self):
        return f"Preference: {self.user} - {self.type} - {'enabled' if self.enabled else 'disabled'}"
