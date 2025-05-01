from django.test import TestCase
from django.contrib.auth import get_user_model
from credit_workflow.models import CreditRequest, CounterParty
from workflow.models import WorkflowState
from rest_framework.test import APIClient

User = get_user_model()

class CreditRequestModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analyst', password='pass')
        self.state = WorkflowState.objects.create(state_id='DRFT1', name='Draft', description='Draft state')
        self.counterparty = CounterParty.objects.create(
            name='Test Counterparty',
            cif_number='CIF10001',
            country_of_risk='Testland'
        )
        self.business_sponsor = User.objects.create_user(username='sponsor', password='pass')
        self.credit_request = CreditRequest.objects.create(
            request_number='CR-001',
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

    def test_credit_request_creation(self):
        self.assertEqual(self.credit_request.request_number, 'CR-001')
        self.assertEqual(self.credit_request.workflow_state.name, 'Draft')
        self.assertEqual(self.credit_request.submitter.username, 'analyst')

class CreditRequestAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='pass', role='analyst')
        self.state = WorkflowState.objects.create(state_id='DRFT2', name='Draft', description='Draft state')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.counterparty = CounterParty.objects.create(
            name='Test Counterparty',
            cif_number='CIF10002',
            country_of_risk='Testland'
        )
        self.business_sponsor = User.objects.create_user(username='sponsor', password='pass')
        self.credit_request = CreditRequest.objects.create(
            request_number='CR-002',
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

    def test_list_credit_requests(self):
        response = self.client.get('/api/credit-requests/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(cr['request_number'] == 'CR-002' for cr in response.data))

    def test_transition_action(self):
        new_state = WorkflowState.objects.create(state_id='SUBMIT1', name='Submitted', description='Submitted')
        # Add the missing transition
        from workflow.models import WorkflowStateTransition
        WorkflowStateTransition.objects.create(
            from_state=self.state,
            to_state=new_state,
            required_roles='analyst',
            name='submit'
        )
        response = self.client.post(
            f'/api/credit-requests/{self.credit_request.id}/transition/',
            {'to_state_id': new_state.id, 'action_name': 'submit'}
        )
        self.assertEqual(response.status_code, 200)
        self.credit_request.refresh_from_db()
        self.assertEqual(self.credit_request.workflow_state, new_state)
