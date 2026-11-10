from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from products.models import Product
from clients.models import Client as ClientModel
from construction.models import ClientProject, ClientInventory, DailyConstructionEntry
from accounts.models import UserProfile


class ConstructionTrackingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('const_admin', 'c@test.com', 'Pass123!')
        self.admin.profile.role = UserProfile.ROLE_SUPERADMIN
        self.admin.profile.save()

        self.product = Product.objects.create(
            name='Solid Concrete Brick',
            code='BRK-CONC-01',
            selling_price=Decimal('25.00')
        )
        # Factory stock starts at 5000
        factory_inv = self.product.inventory
        factory_inv.opening_stock = 5000
        factory_inv.recalculate()
        factory_inv.save()

        self.customer = ClientModel.objects.create(
            name='Apex Constructions',
            code='CLT-APX-01',
            phone='9998887776'
        )

        self.project = ClientProject.objects.create(
            client=self.customer,
            name='Apex Residency Project'
        )

        # Site has received 800 bricks via prior dispatch
        self.site_inv = ClientInventory.objects.create(
            project=self.project,
            product=self.product,
            opening_stock=0,
            total_received=800,
            total_used=0
        )
        self.site_inv.recalculate()
        self.site_inv.save()

    def test_construction_usage_reduces_client_stock_without_affecting_factory_stock(self):
        self.client.login(username='const_admin', password='Pass123!')

        initial_factory_stock = self.product.inventory.current_stock  # 5000
        initial_site_stock = self.site_inv.current_stock              # 800

        data = {
            'date': '2026-11-10',
            'number_of_workers': 8,
            'work_progress_percentage': 25,
            'work_completed_today': 'Completed ground floor brick masonry',
            'notes': 'Good weather, smooth progress',
            'material_usages-TOTAL_FORMS': '1',
            'material_usages-INITIAL_FORMS': '0',
            'material_usages-MIN_NUM_FORMS': '0',
            'material_usages-MAX_NUM_FORMS': '1000',
            'material_usages-0-product': self.product.id,
            'material_usages-0-quantity_used': '350',
            'material_usages-0-notes': 'Ground floor outer walls',
        }

        response = self.client.post(
            reverse('construction:daily_entry_create', kwargs={'project_id': self.project.id}),
            data
        )
        self.assertEqual(response.status_code, 302)

        # 1. Site stock must be reduced: 800 - 350 = 450
        self.site_inv.refresh_from_db()
        self.assertEqual(self.site_inv.total_used, 350)
        self.assertEqual(self.site_inv.current_stock, 450)

        # 2. CRITICAL MANDATORY BUSINESS RULE: Factory stock MUST NOT be reduced!
        self.product.inventory.refresh_from_db()
        self.assertEqual(self.product.inventory.current_stock, initial_factory_stock)
        self.assertEqual(self.product.inventory.current_stock, 5000)

    def test_prevent_negative_client_stock(self):
        self.client.login(username='const_admin', password='Pass123!')

        # Available site stock is 800. Trying to use 1200 bricks.
        data = {
            'date': '2026-11-10',
            'number_of_workers': 5,
            'work_progress_percentage': 30,
            'work_completed_today': 'Wall work',
            'material_usages-TOTAL_FORMS': '1',
            'material_usages-INITIAL_FORMS': '0',
            'material_usages-MIN_NUM_FORMS': '0',
            'material_usages-MAX_NUM_FORMS': '1000',
            'material_usages-0-product': self.product.id,
            'material_usages-0-quantity_used': '1200',
        }

        response = self.client.post(
            reverse('construction:daily_entry_create', kwargs={'project_id': self.project.id}),
            data
        )
        # Should fail validation and re-render form
        self.assertEqual(response.status_code, 200)

        # Site stock must remain untouched (800)
        self.site_inv.refresh_from_db()
        self.assertEqual(self.site_inv.current_stock, 800)
