from django.test import TestCase
from django.contrib.auth import get_user_model
from workflow.models import WorkflowState, WorkflowStateTransition
from credit_workflow.models import CreditRequest, CounterParty
from workflow.services import WorkflowEngine
from users.models import User

class WorkflowStateModelTest(TestCase):
    def test_create_workflow_state(self):
        state = WorkflowState.objects.create(state_id='S1', name='Draft', description='Draft state')
        self.assertEqual(state.name, 'Draft')

class WorkflowStateTransitionModelTest(TestCase):
    def test_is_allowed_for_user(self):
        state = WorkflowState.objects.create(state_id='S1', name='Draft', description='Draft state')
        next_state = WorkflowState.objects.create(state_id='S2', name='Submitted', description='Submitted')
        transition = WorkflowStateTransition.objects.create(from_state=state, to_state=next_state, required_roles='analyst')
        user = User.objects.create_user(username='analyst', password='pass', role='analyst')
        self.assertTrue(transition.is_allowed_for_user(user))

class WorkflowEngineTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analyst', password='pass', role='analyst')
        self.state = WorkflowState.objects.create(state_id='S1', name='Draft', description='Draft state')
        self.next_state = WorkflowState.objects.create(state_id='S2', name='Submitted', description='Submitted')
        self.transition = WorkflowStateTransition.objects.create(from_state=self.state, to_state=self.next_state, required_roles='analyst', name='submit')
        self.counterparty = CounterParty.objects.create(
            name='Test Counterparty',
            cif_number='CIF12345',
            country_of_risk='Testland'
        )
        self.business_sponsor = User.objects.create_user(username='sponsor', password='pass', role='sponsor')
        self.credit_request = CreditRequest.objects.create(
            request_number='CR-006',
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

    def test_transition_request(self):
        result = WorkflowEngine.transition_request(self.credit_request, self.next_state, self.user, action_name='submit')
        self.assertEqual(result.workflow_state, self.next_state)

    def test_get_available_transitions(self):
        transitions = WorkflowEngine.get_available_transitions(self.credit_request, self.user)
        self.assertIn(self.transition, transitions)
