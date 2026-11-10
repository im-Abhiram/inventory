from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from products.models import Product
from inventory.models import StockTransaction
from production.models import ProductionEntry
from accounts.models import UserProfile


class ProductionManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('prod_admin', 'p@test.com', 'Pass123!')
        self.admin.profile.role = UserProfile.ROLE_SUPERADMIN
        self.admin.profile.save()

        self.product = Product.objects.create(
            name='Hollow Brick 8 Inch',
            code='BRK-HLW-8',
            selling_price=Decimal('35.00'),
            minimum_stock_level=1000
        )

    def test_production_increases_factory_stock_and_creates_transaction(self):
        self.client.login(username='prod_admin', password='Pass123!')
        
        initial_stock = self.product.inventory.current_stock
        self.assertEqual(initial_stock, 0)

        response = self.client.post(reverse('production:production_create'), {
            'production_date': '2026-11-10',
            'product': self.product.id,
            'quantity': 2500,
            'shift': 'Morning',
            'worker_count': 6,
            'notes': 'Batch A-1',
            'submission_token': 'token_prod_1'
        })
        self.assertEqual(response.status_code, 302)

        # Factory inventory refreshed
        self.product.inventory.refresh_from_db()
        self.assertEqual(self.product.inventory.current_stock, 2500)
        self.assertEqual(self.product.inventory.total_production, 2500)

        # StockTransaction check
        tx = StockTransaction.objects.filter(product=self.product, transaction_type='PRODUCTION').first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.quantity, 2500)
        self.assertEqual(tx.balance_after, 2500)

    def test_duplicate_production_prevention(self):
        self.client.login(username='prod_admin', password='Pass123!')
        
        # Submit first time
        self.client.post(reverse('production:production_create'), {
            'production_date': '2026-11-10',
            'product': self.product.id,
            'quantity': 1000,
            'shift': 'Morning',
            'worker_count': 4,
            'submission_token': 'unique_token_123'
        })

        # Submit again with same token (e.g. user double-clicked)
        self.client.post(reverse('production:production_create'), {
            'production_date': '2026-11-10',
            'product': self.product.id,
            'quantity': 1000,
            'shift': 'Morning',
            'worker_count': 4,
            'submission_token': 'unique_token_123'
        })

        # Only 1 entry should exist and stock should be 1000, not 2000
        self.assertEqual(ProductionEntry.objects.count(), 1)
        self.product.inventory.refresh_from_db()
        self.assertEqual(self.product.inventory.current_stock, 1000)


    def test_production_edit_adjusts_inventory_difference(self):
        self.client.login(username='prod_admin', password='Pass123!')

        # Initial production of 1000
        entry = ProductionEntry.objects.create(
            production_date='2026-11-10',
            product=self.product,
            quantity=1000,
            shift='Morning',
            worker_count=4,
            created_by=self.admin
        )
        self.product.inventory.total_production = 1000
        self.product.inventory.recalculate()
        self.product.inventory.save()
        self.assertEqual(self.product.inventory.current_stock, 1000)

        # Edit entry to 1500 (difference of +500)
        response = self.client.post(reverse('production:production_edit', args=[entry.id]), {
            'production_date': '2026-11-10',
            'product': self.product.id,
            'quantity': 1500,
            'shift': 'Afternoon',
            'worker_count': 5,
            'notes': 'Corrected quantity'
        })
        self.assertEqual(response.status_code, 302)

        entry.refresh_from_db()
        self.assertEqual(entry.quantity, 1500)
        self.assertEqual(entry.shift, 'Afternoon')

        self.product.inventory.refresh_from_db()
        self.assertEqual(self.product.inventory.total_production, 1500)
        self.assertEqual(self.product.inventory.current_stock, 1500)

        # Check adjustment transaction
        adj_tx = StockTransaction.objects.filter(
            product=self.product,
            transaction_type=StockTransaction.TYPE_ADJUSTMENT_ADD
        ).last()
        self.assertIsNotNone(adj_tx)
        self.assertEqual(adj_tx.quantity, 500)
        self.assertEqual(adj_tx.balance_after, 1500)
