from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from documents.models import Document, DocumentType
from users.models import User

class DocumentService:
    """
    Service for document management: versioning, draft/finalization, permissions, and business logic.
    """
    @staticmethod
    @transaction.atomic
    def create_new_version(document: Document, user: User, file, description=None):
        """
        Create a new version of a document, setting previous_version and incrementing version number.
        Only allowed if the user has permission (e.g., is uploader or admin).
        """
        if document.uploaded_by != user and not user.is_superuser:
            raise PermissionDenied("You do not have permission to create a new version of this document.")
        new_version = Document.objects.create(
            credit_request=document.credit_request,
            document_type=document.document_type,
            file=file,
            version=document.version + 1,
            is_draft=True,
            uploaded_by=user,
            description=description or document.description,
            previous_version=document,
        )
        return new_version

    @staticmethod
    @transaction.atomic
    def finalize_document(document: Document, user: User):
        """
        Finalize (publish) a document version. Only allowed if user is uploader or admin.
        """
        if document.uploaded_by != user and not user.is_superuser:
            raise PermissionDenied("You do not have permission to finalize this document.")
        if not document.is_draft:
            raise ValidationError("Document is already finalized.")
        document.is_draft = False
        document.save(update_fields=["is_draft"])
        # (Optional) Trigger notifications or workflow hooks here
        return document

    @staticmethod
    def can_edit(document: Document, user: User):
        """
        Check if the user can edit the document (uploader or admin, and draft status).
        """
        return (document.uploaded_by == user or user.is_superuser) and document.is_draft

    @staticmethod
    def get_latest_version(credit_request, document_type):
        """
        Get the latest (highest version) document for a given credit request and document type.
        """
        return Document.objects.filter(
            credit_request=credit_request,
            document_type=document_type
        ).order_by('-version').first()
