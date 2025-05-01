from django.contrib import admin
from .models import DocumentType, Document

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("credit_request", "document_type", "version", "is_draft", "uploaded_by", "uploaded_at")
    search_fields = ("credit_request__request_number", "document_type__name", "uploaded_by__username")
    list_filter = ("document_type", "is_draft", "uploaded_at")
    readonly_fields = ("uploaded_at",)
