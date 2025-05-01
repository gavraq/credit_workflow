from django.db import models
from credit_workflow.models import CreditRequest
from users.models import User

class DocumentType(models.Model):
    """
    Optional: Categorizes documents (e.g., Financials, Legal, Questionnaire, etc.)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Document(models.Model):
    """
    Represents a document associated with a CreditRequest, supporting versioning and draft states.
    """
    credit_request = models.ForeignKey(CreditRequest, on_delete=models.CASCADE, related_name="documents")
    document_type = models.ForeignKey(DocumentType, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    version = models.PositiveIntegerField(default=1)
    is_draft = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    previous_version = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='next_versions')

    class Meta:
        unique_together = ("credit_request", "document_type", "version")
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.document_type} v{self.version} for {self.credit_request}"
