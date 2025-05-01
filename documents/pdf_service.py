import io
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from documents.models import Document
from weasyprint import HTML

class PDFService:
    """
    Service for generating PDF documents from Django templates or model data.
    """
    @staticmethod
    def render_document_to_pdf(document: Document, template_name: str, context: dict = None) -> ContentFile:
        """
        Render a Document instance to PDF using a Django template and return as ContentFile.
        """
        if context is None:
            context = {}
        context['document'] = document
        html_string = render_to_string(template_name, context)
        pdf_file = io.BytesIO()
        HTML(string=html_string).write_pdf(target=pdf_file)
        pdf_file.seek(0)
        return ContentFile(pdf_file.read(), name=f"{document.pk}_v{document.version}.pdf")

    @staticmethod
    def attach_pdf_to_document(document: Document, template_name: str, context: dict = None):
        """
        Generate a PDF for the given document and attach it to the Document instance.
        """
        pdf_content = PDFService.render_document_to_pdf(document, template_name, context)
        document.pdf_file.save(pdf_content.name, pdf_content, save=True)
        return document
