from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from clients.models import Client as ClientModel
from products.models import Product
from dispatch.models import Dispatch, DispatchItem
from finance.models import Payment, ClientAccount
from accounts.models import UserProfile


class FinanceManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.accountant = User.objects.create_user('fin_accountant', password='Pass123!')
        self.accountant.profile.role = UserProfile.ROLE_ACCOUNTANT
        self.accountant.profile.save()

        self.customer = ClientModel.objects.create(
            name='Modern Developers',
            code='CLT-MOD-01',
            phone='9845012345',
            opening_balance=Decimal('5000.00'),
            credit_limit=Decimal('50000.00')
        )
        # Outstanding is opening balance (5000)
        self.customer.account.recalculate()

    def test_payment_updates_outstanding_balance(self):
        self.client.login(username='fin_accountant', password='Pass123!')

        # Record payment of 3000
        response = self.client.post(reverse('finance:payment_create'), {
            'client': self.customer.id,
            'payment_date': '2026-11-10',
            'amount': '3000.00',
            'payment_method': 'Bank Transfer',
            'reference_number': 'NEFT-12345678',
            'submission_token': 'pay_tok_1'
        })
        self.assertEqual(response.status_code, 302)

        # Expected outstanding balance: 5000 (opening) - 3000 (payment) = 2000
        self.customer.account.refresh_from_db()
        self.assertEqual(self.customer.account.total_paid, Decimal('3000.00'))
        self.assertEqual(self.customer.account.current_balance, Decimal('2000.00'))

    def test_credit_limit_and_available_credit_calculation(self):
        # Credit limit = 50,000, current balance = 5,000
        # Available credit = 45,000
        self.assertEqual(self.customer.available_credit, Decimal('45000.00'))
        self.assertFalse(self.customer.is_credit_exceeded)

        # Create actual dispatch of 60,000
        Dispatch.objects.create(
            dispatch_number='DSP-TEST-CREDIT-01',
            client=self.customer,
            total_amount=Decimal('60000.00')
        )
        self.customer.account.recalculate()

        # Balance = 5000 + 60000 = 65000 (Exceeds 50000 limit)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_credit_exceeded)
        self.assertEqual(self.customer.available_credit, Decimal('-15000.00'))

    def test_duplicate_payment_submission_prevention(self):
        self.client.login(username='fin_accountant', password='Pass123!')

        data = {
            'client': self.customer.id,
            'payment_date': '2026-11-10',
            'amount': '1500.00',
            'payment_method': 'Cash',
            'submission_token': 'idempotent_token_xyz'
        }

        # First post
        self.client.post(reverse('finance:payment_create'), data)
        # Second post with identical token
        self.client.post(reverse('finance:payment_create'), data)

        # Only one payment record should exist
        self.assertEqual(Payment.objects.filter(client=self.customer).count(), 1)
        self.customer.account.refresh_from_db()
        self.assertEqual(self.customer.account.total_paid, Decimal('1500.00'))
