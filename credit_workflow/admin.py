from django.contrib import admin
from .models import CounterParty, CreditRequest, CreditQuestionnaire, LegalReview, CreditAnalysis, CreditPaper, CreditLimit, LimitType, Document, Notification, NotificationPreference

@admin.register(CounterParty)
class CounterPartyAdmin(admin.ModelAdmin):
    list_display = ("name", "cif_number", "country_of_risk", "business_description", "created_at")
    search_fields = ("name", "cif_number", "country_of_risk")
    list_filter = ("country_of_risk",)

@admin.register(CreditRequest)
class CreditRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "request_number", "counterparty", "workflow_state", "submitter", "assigned_analyst", "business_sponsor", "priority", "da_level", "created_at", "submitted_at")
    search_fields = ("request_number", "counterparty__name", "submitter__username")
    list_filter = ("priority", "workflow_state", "created_at")

@admin.register(CreditQuestionnaire)
class CreditQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ("credit_request", "author", "is_draft", "created_at", "updated_at")
    search_fields = ("credit_request__request_number", "author__username")
    list_filter = ("is_draft", "created_at")

@admin.register(LegalReview)
class LegalReviewAdmin(admin.ModelAdmin):
    list_display = ("credit_request", "reviewer", "is_draft", "created_at", "updated_at")
    search_fields = ("credit_request__request_number", "reviewer__username")
    list_filter = ("is_draft", "created_at")

@admin.register(CreditAnalysis)
class CreditAnalysisAdmin(admin.ModelAdmin):
    list_display = ("credit_request", "analyst", "is_draft", "created_at", "updated_at")
    search_fields = ("credit_request__request_number", "analyst__username")
    list_filter = ("is_draft", "created_at")

@admin.register(CreditPaper)
class CreditPaperAdmin(admin.ModelAdmin):
    list_display = ("credit_request", "compiled_by", "is_draft", "created_at", "updated_at")
    search_fields = ("credit_request__request_number", "compiled_by__username")
    list_filter = ("is_draft", "created_at")
    readonly_fields = ("created_at", "updated_at")

@admin.register(LimitType)
class LimitTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(CreditLimit)
class CreditLimitAdmin(admin.ModelAdmin):
    list_display = ('credit_request', 'limit_type', 'existing_limit_amount', 'proposed_limit_amount')
    search_fields = ('credit_request__request_number',)
    list_filter = ('limit_type',)
