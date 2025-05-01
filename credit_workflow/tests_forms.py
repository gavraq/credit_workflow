from django.test import TestCase
from credit_workflow.forms import CreditRequestForm, CreditLimitForm, CounterPartyForm
from credit_workflow.models import CreditRequest, CreditLimit, CounterParty
from django.contrib.auth import get_user_model
from workflow.models import WorkflowState
from datetime import date

User = get_user_model()

class CreditRequestFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='rm', password='pass')
        self.state = WorkflowState.objects.create(state_id='DRFT1', name='Draft', description='Draft')
        self.counterparty = CounterParty.objects.create(
            name='TestCo', cif_number='CIF10003', country_of_risk='Testland'
        )
        self.sponsor = User.objects.create_user(username='sponsor', password='pass')

    def test_valid_credit_request_form(self):
        form = CreditRequestForm(data={
            'request_number': 'CR-003',
            'counterparty': self.counterparty.id,
            'da_level': 2,
            'priority': 'Medium',
            'required_by_date': date.today(),
            'priority_justification': '',
            'business_sponsor': self.sponsor.id,
        })
        self.assertTrue(form.is_valid())

    def test_high_priority_requires_justification(self):
        form = CreditRequestForm(data={
            'request_number': 'CR-004',
            'counterparty': self.counterparty.id,
            'da_level': 2,
            'priority': 'High',
            'required_by_date': date.today(),
            'priority_justification': '',  # Missing justification
            'business_sponsor': self.sponsor.id,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('priority_justification', form.errors)

class CreditLimitFormTests(TestCase):
    def setUp(self):
        self.counterparty = CounterParty.objects.create(
            name='TestCo', cif_number='CIF10004', country_of_risk='Testland'
        )
        self.user = User.objects.create_user(username='analyst2', password='pass')
        self.state = WorkflowState.objects.create(state_id='DRFT3', name='Draft', description='Draft')
        self.credit_request = CreditRequest.objects.create(
            request_number='CR-005',
            counterparty=self.counterparty,
            submitter=self.user,
            workflow_state=self.state,
            da_level=1,
            business_sponsor=self.user,
            priority='Low',
            required_by_date='2025-12-31',
            revenue_last_12m=1000000.00,
            projected_revenue=1200000.00,
            projected_rorwa_percentage=10.0,
            country_risk_limit_confirmed=True,
            client_introduction_details='Intro',
            kyc_approval_status='Approved',
            senior_client_contact='Contact',
            last_client_visit_date='2025-01-01',
            has_legal_opinion=False,
            financial_statements_received=True,
            submitted_at='2025-04-20T10:00:00+01:00',
        )

    def test_valid_credit_limit_form(self):
        form = CreditLimitForm(data={
            'credit_request': self.credit_request.id,
            'limit_type': 'TRADING_PRE_SETTLEMENT',
            'existing_limit_amount': 100000,
            'existing_tenor_months': 12,
            'proposed_limit_amount': 150000,
            'proposed_tenor_months': 18,
        })
        self.assertTrue(form.is_valid())

    def test_missing_required_fields(self):
        form = CreditLimitForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('credit_request', form.errors)
        self.assertIn('limit_type', form.errors)

class CounterPartyFormTests(TestCase):
    def test_valid_counterparty_form(self):
        form = CounterPartyForm(data={
            'name': 'Acme Corp',
            'cif_number': 'CIF20001',
            'country_of_risk': 'CountryX',
            'business_description': 'A trading company',
            'has_guarantor': False,
            'guarantor_details': '',
            'rating_current': 'A',
            'rating_previous': 'BBB',
            'sp_rating': 'A-',
            'moodys_rating': 'A3',
            'fitch_rating': 'A',
        })
        self.assertTrue(form.is_valid())

    def test_missing_required_fields(self):
        form = CounterPartyForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('cif_number', form.errors)
        self.assertIn('country_of_risk', form.errors)
