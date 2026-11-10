from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from accounts.models import UserProfile
from products.models import Product, ProductCategory
from inventory.models import FactoryInventory, StockTransaction, ProductPurchase
from clients.models import Client
from construction.models import ClientProject, ClientInventory
from finance.models import ExpenseCategory, Payment, Expense
from workers.models import Worker, WorkerAttendance
from production.models import ProductionEntry
from dispatch.models import Dispatch, DispatchItem


class Command(BaseCommand):
    help = 'Seeds initial demo data for the Brick Manufacturing System'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Brick Manufacturing System initial data..."))

        # 1. Create Default Users
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@thamarayyath.com',
                'first_name': 'Factory',
                'last_name': 'Manager',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('Admin@1234')
            admin_user.save()
            admin_user.profile.role = UserProfile.ROLE_SUPERADMIN
            admin_user.profile.save()
            self.stdout.write(self.style.SUCCESS("Created Super Admin user: admin / Admin@1234"))

        accountant_user, created = User.objects.get_or_create(
            username='accountant',
            defaults={
                'email': 'accounts@thamarayyath.com',
                'first_name': 'Chief',
                'last_name': 'Accountant',
            }
        )
        if created:
            accountant_user.set_password('Accounts@1234')
            accountant_user.save()
            accountant_user.profile.role = UserProfile.ROLE_ACCOUNTANT
            accountant_user.profile.save()
            self.stdout.write(self.style.SUCCESS("Created Accountant user: accountant / Accounts@1234"))

        owner_user, created = User.objects.get_or_create(
            username='owner',
            defaults={
                'email': 'owner@thamarayyath.com',
                'first_name': 'Business',
                'last_name': 'Owner',
            }
        )
        if created:
            owner_user.set_password('Owner@1234')
            owner_user.save()
            owner_user.profile.role = UserProfile.ROLE_OWNER
            owner_user.profile.save()
            self.stdout.write(self.style.SUCCESS("Created Owner user: owner / Owner@1234"))

        # 2. Expense Categories
        categories = [
            'Transport', 'Fuel', 'Electricity', 'Worker wages',
            'Maintenance', 'Raw materials', 'Vehicle expenses', 'Office expenses', 'Other'
        ]
        for name in categories:
            ExpenseCategory.objects.get_or_create(name=name)

        # 3. Product Categories
        cat_hollow, _ = ProductCategory.objects.get_or_create(name='Hollow Bricks', defaults={'description': 'Vibrated hollow concrete blocks'})
        cat_interlock, _ = ProductCategory.objects.get_or_create(name='Interlock Pavers', defaults={'description': 'Heavy duty pavement interlocking blocks'})
        cat_solid, _ = ProductCategory.objects.get_or_create(name='Solid Bricks', defaults={'description': 'Standard solid concrete building bricks'})

        # 4. Products
        p1, _ = Product.objects.get_or_create(
            code='BRK-HLW-6',
            defaults={
                'name': 'Hollow Brick 6-Inch',
                'category': cat_hollow,
                'unit': 'Pieces',
                'selling_price': Decimal('32.00'),
                'minimum_stock_level': 1000,
                'description': '400x200x150 mm hollow block for load bearing walls'
            }
        )
        p2, _ = Product.objects.get_or_create(
            code='BRK-HLW-8',
            defaults={
                'name': 'Hollow Brick 8-Inch',
                'category': cat_hollow,
                'unit': 'Pieces',
                'selling_price': Decimal('40.00'),
                'minimum_stock_level': 800,
                'description': '400x200x200 mm heavy load-bearing hollow block'
            }
        )
        p3, _ = Product.objects.get_or_create(
            code='INT-80-ZIG',
            defaults={
                'name': 'Interlock Brick 80mm Zigzag',
                'category': cat_interlock,
                'unit': 'Pieces',
                'selling_price': Decimal('45.00'),
                'minimum_stock_level': 1200,
                'description': 'High strength M40 grade interlock pavers'
            }
        )
        p4, _ = Product.objects.get_or_create(
            code='BRK-SLD-4',
            defaults={
                'name': 'Solid Brick 4-Inch Partition',
                'category': cat_solid,
                'unit': 'Pieces',
                'selling_price': Decimal('24.00'),
                'minimum_stock_level': 1500,
                'description': 'Dense solid brick for boundary walls and partitions'
            }
        )

        # Seed initial inventory
        for prod, stock in [(p1, 4500), (p2, 3200), (p3, 6000), (p4, 5000)]:
            inv, _ = FactoryInventory.objects.get_or_create(product=prod)
            if inv.opening_stock == 0 and inv.current_stock == 0:
                inv.opening_stock = stock
                inv.recalculate()
                inv.save()
                StockTransaction.objects.get_or_create(
                    product=prod,
                    transaction_type=StockTransaction.TYPE_OPENING,
                    defaults={
                        'quantity': stock,
                        'balance_after': stock,
                        'reference': 'INITIAL-SETUP',
                        'notes': 'Initial plant opening inventory setup',
                        'created_by': admin_user
                    }
                )

        # 5. Workers
        workers_data = [
            ('Raju K.', 'Mason', Decimal('950.00'), '+91 98470 11111'),
            ('Suresh Kumar', 'Machine Operator', Decimal('850.00'), '+91 98470 22222'),
            ('Manoj Das', 'Helper', Decimal('650.00'), '+91 98470 33333'),
            ('Babu P.', 'Driver', Decimal('800.00'), '+91 98470 44444'),
            ('Shaji Varghese', 'Supervisor', Decimal('1100.00'), '+91 98470 55555'),
        ]
        for name, w_type, wage, phone in workers_data:
            Worker.objects.get_or_create(
                name=name,
                defaults={
                    'worker_type': w_type,
                    'daily_wage': wage,
                    'phone': phone,
                }
            )

        # 6. Clients
        c1, _ = Client.objects.get_or_create(
            code='CLT-SKY-01',
            defaults={
                'name': 'Skyline Builders & Developers',
                'contact_person': 'Alex Mathew',
                'phone': '+91 94471 23456',
                'location': 'Kochi',
                'address': 'Marine Drive, Kochi, Kerala',
                'opening_balance': Decimal('12000.00'),
                'credit_limit': Decimal('150000.00'),
            }
        )
        c2, _ = Client.objects.get_or_create(
            code='CLT-GRN-02',
            defaults={
                'name': 'Greenfield Construction Co.',
                'contact_person': 'Anil Kumar',
                'phone': '+91 94472 34567',
                'location': 'Kottayam',
                'address': 'Collectorate Junction, Kottayam',
                'payment_type': Client.PAYMENT_TYPE_CREDIT,
                'opening_balance': Decimal('0.00'),
                'credit_limit': Decimal('80000.00'),
            }
        )
        c3, _ = Client.objects.get_or_create(
            name='Anand Direct Retail Builders',
            defaults={
                'contact_person': 'Anand R.',
                'phone': '+91 94473 45678',
                'location': 'Aluva',
                'address': 'NH By-pass, Aluva',
                'payment_type': Client.PAYMENT_TYPE_CASH,
                'opening_balance': Decimal('0.00'),
                'credit_limit': Decimal('0.00'),
            }
        )

        # 7. Initial Product Purchase
        pur, pur_created = ProductPurchase.objects.get_or_create(
            purchase_number='PUR-20261110-0001',
            defaults={
                'purchase_date': timezone.now().date(),
                'supplier_name': 'Kerala Clinker & Aggregates Ltd.',
                'invoice_number': 'KCA/2026/894',
                'product': p1,
                'quantity': 500,
                'unit_price': Decimal('22.00'),
                'total_amount': Decimal('11000.00'),
                'payment_status': 'Paid',
                'payment_method': 'Bank Transfer',
                'created_by': admin_user,
                'notes': 'Initial bulk purchase for inventory ramp-up'
            }
        )
        if pur_created:
            inv1, _ = FactoryInventory.objects.get_or_create(product=p1)
            inv1.total_additions += 500
            inv1.recalculate()
            inv1.save()

        # 8. Construction Projects
        p_sky, _ = ClientProject.objects.get_or_create(
            client=c1,
            name='Skyline Ocean View Tower',
            defaults={
                'location': 'Marine Drive Plot 4, Kochi',
                'status': ClientProject.STATUS_ACTIVE,
                'description': '14-storey residential apartment project'
            }
        )
        p_grn, _ = ClientProject.objects.get_or_create(
            client=c2,
            name='Greenfield Commercial Complex',
            defaults={
                'location': 'Nagampadam, Kottayam',
                'status': ClientProject.STATUS_ACTIVE,
                'description': 'Commercial showroom and retail complex'
            }
        )

        # Ensure ClientAccounts are fresh
        if hasattr(c1, 'account'):
            c1.account.recalculate()
        if hasattr(c2, 'account'):
            c2.account.recalculate()

        self.stdout.write(self.style.SUCCESS("Database successfully initialized with initial demonstration data!"))

