from django.test import TestCase
from django.contrib.auth import get_user_model
from documents.models import Document, DocumentType
from credit_workflow.models import CreditRequest, CounterParty
from workflow.models import WorkflowState
from documents.services import DocumentService
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class DocumentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='docuser', password='pass')
        self.state = WorkflowState.objects.create(name='Draft', description='Draft state')
        self.counterparty = CounterParty.objects.create(
            name='Test Counterparty',
            cif_number='CIF20001',
            country_of_risk='Testland'
        )
        self.business_sponsor = User.objects.create_user(username='sponsor', password='pass')
        self.credit_request = CreditRequest.objects.create(
            request_number='CR-003',
            counterparty=self.counterparty,
            submitter=self.user,
            workflow_state=self.state,
            assigned_analyst=None,
            business_sponsor=self.business_sponsor,
            second_sponsor=None,
            da_level=1,
            priority='Medium',
            required_by_date='2025-12-31',
            priority_justification='Test justification',
            revenue_last_12m=1000000.00,
            projected_revenue=1200000.00,
            projected_rorwa_percentage=10.0,
            country_risk_limit_confirmed=True,
            client_introduction_details='Test details',
            kyc_approval_status='Approved',
            senior_client_contact='John Doe',
            last_client_visit_date='2025-01-01',
            has_legal_opinion=False,
            financial_statements_received=True,
            interim_financials_info='',
            submitted_at='2025-04-20T09:49:22+01:00',
            completed_at=None
        )
        self.doc_type = DocumentType.objects.create(name='Credit Memo')
        self.document = Document.objects.create(
            credit_request=self.credit_request,
            document_type=self.doc_type,
            uploaded_by=self.user,
            version=1,
            is_draft=True,
            description='Initial memo'
        )

    def test_document_creation(self):
        self.assertEqual(self.document.version, 1)
        self.assertTrue(self.document.is_draft)
        self.assertEqual(self.document.uploaded_by.username, 'docuser')

class DocumentServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='docuser', password='pass')
        self.state = WorkflowState.objects.create(name='Draft', description='Draft state')
        self.counterparty = CounterParty.objects.create(
            name='Test Counterparty',
            cif_number='CIF20002',
            country_of_risk='Testland'
        )
        self.business_sponsor = User.objects.create_user(username='sponsor', password='pass')
        self.credit_request = CreditRequest.objects.create(
            request_number='CR-004',
            counterparty=self.counterparty,
            submitter=self.user,
            workflow_state=self.state,
            assigned_analyst=None,
            business_sponsor=self.business_sponsor,
            second_sponsor=None,
            da_level=1,
            priority='Low',
            required_by_date='2025-12-31',
            priority_justification='Test justification',
            revenue_last_12m=1000000.00,
            projected_revenue=1200000.00,
            projected_rorwa_percentage=10.0,
            country_risk_limit_confirmed=True,
            client_introduction_details='Test details',
            kyc_approval_status='Approved',
            senior_client_contact='John Doe',
            last_client_visit_date='2025-01-01',
            has_legal_opinion=False,
            financial_statements_received=True,
            interim_financials_info='',
            submitted_at='2025-04-20T09:49:22+01:00',
            completed_at=None
        )
        self.doc_type = DocumentType.objects.create(name='Credit Memo')
        self.document = Document.objects.create(
            credit_request=self.credit_request,
            document_type=self.doc_type,
            uploaded_by=self.user,
            version=1,
            is_draft=True,
            description='Initial memo'
        )

    def test_create_new_version(self):
        file = SimpleUploadedFile('test.pdf', b'filecontent')
        new_doc = DocumentService.create_new_version(self.document, self.user, file, 'v2')
        self.assertEqual(new_doc.version, 2)
        self.assertEqual(new_doc.previous_version, self.document)
        self.assertEqual(new_doc.uploaded_by, self.user)

class DocumentAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='pass')
        self.state = WorkflowState.objects.create(name='Draft', description='Draft state')
        self.counterparty = CounterParty.objects.create(
            name='Test Counterparty',
            cif_number='CIF20003',
            country_of_risk='Testland'
        )
        self.business_sponsor = User.objects.create_user(username='sponsor', password='pass')
        self.credit_request = CreditRequest.objects.create(
            request_number='CR-005',
            counterparty=self.counterparty,
            submitter=self.user,
            workflow_state=self.state,
            assigned_analyst=None,
            business_sponsor=self.business_sponsor,
            second_sponsor=None,
            da_level=1,
            priority='High',
            required_by_date='2025-12-31',
            priority_justification='Test justification',
            revenue_last_12m=1000000.00,
            projected_revenue=1200000.00,
            projected_rorwa_percentage=10.0,
            country_risk_limit_confirmed=True,
            client_introduction_details='Test details',
            kyc_approval_status='Approved',
            senior_client_contact='John Doe',
            last_client_visit_date='2025-01-01',
            has_legal_opinion=False,
            financial_statements_received=True,
            interim_financials_info='',
            submitted_at='2025-04-20T09:49:22+01:00',
            completed_at=None
        )
        self.doc_type = DocumentType.objects.create(name='Credit Memo')
        self.document = Document.objects.create(
            credit_request=self.credit_request,
            document_type=self.doc_type,
            uploaded_by=self.user,
            version=1,
            is_draft=True,
            description='Initial memo'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_documents(self):
        response = self.client.get('/api/documents/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(doc['description'] == 'Initial memo' for doc in response.data))

    def test_new_version_action(self):
        file = SimpleUploadedFile('test2.pdf', b'filecontent')
        response = self.client.post(
            f'/api/documents/{self.document.id}/new_version/',
            {'file': file, 'description': 'v2'},
            format='multipart'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['version'], 2)

    def test_finalize_action(self):
        response = self.client.post(f'/api/documents/{self.document.id}/finalize/')
        self.assertEqual(response.status_code, 200)
        self.document.refresh_from_db()
        self.assertFalse(self.document.is_draft)
