from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        CREDIT_ANALYST = 'credit_analyst', 'Credit Analyst'
        RELATIONSHIP_MANAGER = 'relationship_manager', 'Relationship Manager'
        LEGAL_REVIEWER = 'legal_reviewer', 'Legal Reviewer'
        CREDIT_APPROVER = 'credit_approver', 'Credit Approver'
        COMMITTEE_MEMBER = 'committee_member', 'Committee Member'
        BUSINESS_SPONSOR = 'business_sponsor', 'Business Sponsor'
        SYSTEM_ADMIN = 'system_admin', 'System Administrator'

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.RELATIONSHIP_MANAGER,
        help_text="Role of the user in the credit workflow system."
    )
    department = models.CharField(max_length=100, blank=True, null=True)
    team = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
