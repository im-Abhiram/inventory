from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from products.models import Product
from clients.models import Client as ClientModel
from construction.models import ClientProject, ClientInventory
from dispatch.models import Dispatch
from accounts.models import UserProfile


class DispatchManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('dsp_admin', 'd@test.com', 'Pass123!')
        self.admin.profile.role = UserProfile.ROLE_SUPERADMIN
        self.admin.profile.save()

        self.product = Product.objects.create(
            name='Interlock Brick 80mm',
            code='INT-80',
            selling_price=Decimal('42.00'),
            minimum_stock_level=500
        )
        # Seed 1000 units in factory stock
        inv = self.product.inventory
        inv.opening_stock = 1000
        inv.recalculate()
        inv.save()

        self.customer = ClientModel.objects.create(
            name='Horizon Infra Pvt Ltd',
            code='CLT-HRZ-01',
            phone='9876543210',
            credit_limit=Decimal('100000.00')
        )

        self.project = ClientProject.objects.create(
            client=self.customer,
            name='Horizon Heights Site'
        )

    def test_dispatch_reduces_factory_stock_and_increases_client_stock(self):
        self.client.login(username='dsp_admin', password='Pass123!')

        data = {
            'dispatch_date': '2026-11-10',
            'client': self.customer.id,
            'project': self.project.id,
            'vehicle_number': 'KL-07-ZZ-9999',
            'driver_name': 'Ramesh',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-product': self.product.id,
            'items-0-quantity': '400',
            'items-0-unit_price': '42.00',
        }

        response = self.client.post(reverse('dispatch:dispatch_create'), data)
        self.assertEqual(response.status_code, 302)

        # 1. Factory stock reduced: 1000 - 400 = 600
        self.product.inventory.refresh_from_db()
        self.assertEqual(self.product.inventory.current_stock, 600)
        self.assertEqual(self.product.inventory.total_dispatch, 400)

        # 2. Client site inventory increased to 400
        site_inv = ClientInventory.objects.filter(project=self.project, product=self.product).first()
        self.assertIsNotNone(site_inv)
        self.assertEqual(site_inv.current_stock, 400)
        self.assertEqual(site_inv.total_received, 400)

        # 3. Client account updated with outstanding balance: 400 * 42 = 16800
        self.customer.account.refresh_from_db()
        self.assertEqual(self.customer.account.current_balance, Decimal('16800.00'))

    def test_prevent_negative_factory_stock(self):
        self.client.login(username='dsp_admin', password='Pass123!')

        # Factory stock is 1000. Attempting to dispatch 1500 units.
        data = {
            'dispatch_date': '2026-11-10',
            'client': self.customer.id,
            'project': self.project.id,
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-product': self.product.id,
            'items-0-quantity': '1500',
            'items-0-unit_price': '42.00',
        }

        response = self.client.post(reverse('dispatch:dispatch_create'), data)
        # Form error should be returned (HTTP 200 re-rendering form)
        self.assertEqual(response.status_code, 200)

        # Ensure no dispatch was saved
        self.assertEqual(Dispatch.objects.count(), 0)

        # Ensure factory stock was NOT altered
        self.product.inventory.refresh_from_db()
        self.assertEqual(self.product.inventory.current_stock, 1000)
