from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from products.models import Product, ProductCategory
from inventory.models import FactoryInventory, StockTransaction
from accounts.models import UserProfile


class FactoryInventoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('inv_admin', 'inv@test.com', 'Pass123!')
        self.user.profile.role = UserProfile.ROLE_SUPERADMIN
        self.user.profile.save()

        self.category = ProductCategory.objects.create(name='Bricks')
        self.product = Product.objects.create(
            name='Solid Brick 6 Inch',
            code='BRK-SLD-6',
            category=self.category,
            selling_price=Decimal('28.50'),
            minimum_stock_level=500
        )

    def test_product_auto_creates_factory_inventory(self):
        inv = FactoryInventory.objects.filter(product=self.product).first()
        self.assertIsNotNone(inv)
        self.assertEqual(inv.current_stock, 0)

    def test_stock_formula_calculation(self):
        inv = self.product.inventory
        inv.opening_stock = 1000
        inv.total_production = 5000
        inv.total_additions = 200
        inv.total_dispatch = 3000
        inv.total_deductions = 100
        inv.recalculate()
        inv.save()

        # Expected: 1000 + 5000 + 200 - 3000 - 100 = 3100
        self.assertEqual(inv.current_stock, 3100)
        self.assertEqual(inv.stock_status, 'In Stock')

    def test_low_stock_detection(self):
        inv = self.product.inventory
        inv.opening_stock = 400
        inv.recalculate()
        inv.save()

        # Threshold is 500, stock is 400
        self.assertTrue(self.product.is_low_stock)
        self.assertEqual(inv.stock_status, 'Low Stock')


from django.urls import reverse
from inventory.models import ProductPurchase


class ProductPurchaseTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser('admin_purchaser', 'purchaser@test.com', 'Pass123!')
        self.user.profile.role = UserProfile.ROLE_SUPERADMIN
        self.user.profile.save()

        self.product = Product.objects.create(
            name='Cement Grade 53',
            code='MAT-CEM-53',
            selling_price=Decimal('420.00'),
            minimum_stock_level=50
        )

    def test_purchase_creation_updates_inventory_and_creates_stock_tx(self):
        self.client.login(username='admin_purchaser', password='Pass123!')
        initial_stock = self.product.inventory.current_stock
        self.assertEqual(initial_stock, 0)

        response = self.client.post(reverse('inventory:purchase_create'), {
            'purchase_date': '2026-11-10',
            'supplier_name': 'UltraTech Direct Supplier',
            'supplier_invoice': 'INV-2026-99',
            'product': self.product.id,
            'quantity': 150,
            'unit_price': '380.00',
            'payment_status': 'Paid',
            'payment_method': 'Bank Transfer',
            'notes': 'Factory stock replenishment'
        })
        self.assertEqual(response.status_code, 302)

        # Verify purchase record created
        purchase = ProductPurchase.objects.filter(product=self.product).first()
        self.assertIsNotNone(purchase)
        self.assertEqual(purchase.quantity, 150)
        self.assertEqual(purchase.total_amount, Decimal('57000.00'))

        # Verify factory inventory additions updated
        self.product.inventory.refresh_from_db()
        self.assertEqual(self.product.inventory.total_additions, 150)
        self.assertEqual(self.product.inventory.current_stock, 150)

        # Verify stock transaction logged
        tx = StockTransaction.objects.filter(product=self.product, transaction_type='PURCHASE').first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.quantity, 150)
        self.assertEqual(tx.balance_after, 150)
