from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import Product, ProductCategory
from inventory.models import FactoryInventory, StockTransaction, StockAdjustment, ProductPurchase
from clients.models import Client
from construction.models import ClientProject, ClientInventory, ClientStockTransaction, ProjectProductPrice, DailyConstructionEntry, DailyMaterialUsage
from finance.models import Payment, Expense, ClientAccount, ExpenseCategory
from workers.models import Worker, WorkerAttendance
from production.models import ProductionEntry
from dispatch.models import Dispatch, DispatchItem


class Command(BaseCommand):
    help = 'Cleans up demonstration factory records (products, inventory, clients, dispatches, transactions) while preserving user accounts.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Confirm deletion of demo business records without interactive prompt'
        )

    def handle(self, *args, **options):
        if not options.get('yes'):
            self.stdout.write(self.style.WARNING(
                "\nWARNING: This command will wipe demonstration products, factory inventory, clients, dispatches, and financial logs."
            ))
            self.stdout.write("User accounts and login credentials will NOT be touched.")
            confirm = input("Are you sure you want to clear demo business data? (yes/no): ").strip().lower()
            if confirm != 'yes':
                self.stdout.write(self.style.NOTICE("Operation cancelled."))
                return

        self.stdout.write(self.style.NOTICE("Clearing demo business records..."))

        with transaction.atomic():
            # 1. Construction & Daily logs
            DailyMaterialUsage.objects.all().delete()
            DailyConstructionEntry.objects.all().delete()
            ClientStockTransaction.objects.all().delete()
            ClientInventory.objects.all().delete()
            ProjectProductPrice.objects.all().delete()
            ClientProject.objects.all().delete()

            # 2. Dispatches
            DispatchItem.objects.all().delete()
            Dispatch.objects.all().delete()

            # 3. Finance
            Payment.objects.all().delete()
            Expense.objects.all().delete()
            ClientAccount.objects.all().delete()

            # 4. Clients
            Client.objects.all().delete()

            # 5. Production & Workers
            ProductionEntry.objects.all().delete()
            WorkerAttendance.objects.all().delete()
            Worker.objects.all().delete()

            # 6. Inventory & Purchases
            ProductPurchase.objects.all().delete()
            StockAdjustment.objects.all().delete()
            StockTransaction.objects.all().delete()
            FactoryInventory.objects.all().delete()

            # 7. Products
            Product.objects.all().delete()
            ProductCategory.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            "\n[OK] Demo business data successfully cleared!"
        ))
        self.stdout.write(
            "Your database is now clean. All dashboards will display 0 until you add your real factory products, inventory, and clients."
        )
