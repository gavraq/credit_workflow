from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from credit_workflow.models import CreditRequest
from documents.models import Document
from notifications.models import Notification
from .serializers import CreditRequestSerializer, DocumentSerializer, NotificationSerializer
from workflow.services import WorkflowEngine
from documents.services import DocumentService
from documents.pdf_service import PDFService
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

class CreditRequestViewSet(viewsets.ModelViewSet):
    queryset = CreditRequest.objects.all()
    serializer_class = CreditRequestSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        credit_request = self.get_object()
        to_state_id = request.data.get('to_state_id')
        action_name = request.data.get('action_name')
        user = request.user
        from workflow.models import WorkflowState
        to_state = WorkflowState.objects.get(pk=to_state_id)
        result = WorkflowEngine.transition_request(
            credit_request,
            to_state,
            user,
            action_name=action_name
        )
        serializer = self.get_serializer(result)
        return Response(serializer.data)

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def new_version(self, request, pk=None):
        document = self.get_object()
        file = request.FILES.get('file')
        description = request.data.get('description')
        user = request.user
        new_doc = DocumentService.create_new_version(document, user, file, description)
        serializer = self.get_serializer(new_doc)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        document = self.get_object()
        user = request.user
        finalized = DocumentService.finalize_document(document, user)
        serializer = self.get_serializer(finalized)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        document = self.get_object()
        pdf_content = PDFService.render_document_to_pdf(document, 'documents/pdf_template.html')
        response = Response(pdf_content.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{document.pk}_v{document.version}.pdf"'
        return response

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
