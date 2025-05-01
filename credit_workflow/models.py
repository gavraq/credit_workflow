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

class LegalReview(models.Model):
    """
    Legal review for a credit request.
    """
    credit_request = models.OneToOneField(CreditRequest, on_delete=models.CASCADE, related_name="legal_review")
    reviewer = models.ForeignKey(User, on_delete=models.PROTECT)
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
