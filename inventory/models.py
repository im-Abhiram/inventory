from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from products.models import Product


class FactoryInventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory')
    opening_stock = models.PositiveIntegerField(default=0)
    total_production = models.PositiveIntegerField(default=0)
    total_additions = models.PositiveIntegerField(default=0)
    total_dispatch = models.PositiveIntegerField(default=0)
    total_deductions = models.PositiveIntegerField(default=0)
    current_stock = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Factory Inventory'
        verbose_name_plural = 'Factory Inventories'

    def __str__(self):
        return f"{self.product.name} - Stock: {self.current_stock}"

    def recalculate(self):
        """
        Recalculates current stock from formula:
        Current Stock = Opening Stock + Production + Additions - Dispatch - Deductions
        """
        self.current_stock = (
            self.opening_stock +
            self.total_production +
            self.total_additions -
            self.total_dispatch -
            self.total_deductions
        )
        return self.current_stock

    @property
    def stock_status(self):
        if self.current_stock <= 0:
            return 'Out of Stock'
        elif self.current_stock <= self.product.minimum_stock_level:
            return 'Low Stock'
        return 'In Stock'

    @property
    def is_low_stock(self):
        return self.current_stock <= self.product.minimum_stock_level


class StockTransaction(models.Model):
    TYPE_OPENING = 'OPENING'
    TYPE_PRODUCTION = 'PRODUCTION'
    TYPE_PURCHASE = 'PURCHASE'
    TYPE_DISPATCH = 'DISPATCH'
    TYPE_ADJUSTMENT_ADD = 'ADJUSTMENT_ADD'
    TYPE_ADJUSTMENT_SUB = 'ADJUSTMENT_SUB'
    TYPE_DISPATCH_REVERSAL = 'DISPATCH_REVERSAL'

    TRANSACTION_TYPES = [
        (TYPE_OPENING, 'Opening Stock'),
        (TYPE_PRODUCTION, 'Production'),
        (TYPE_PURCHASE, 'Purchase / Addition'),
        (TYPE_DISPATCH, 'Dispatch'),
        (TYPE_ADJUSTMENT_ADD, 'Stock Adjustment (+)'),
        (TYPE_ADJUSTMENT_SUB, 'Stock Adjustment (-)'),
        (TYPE_DISPATCH_REVERSAL, 'Dispatch Reversal'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_transactions')
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES, db_index=True)
    quantity = models.PositiveIntegerField()
    balance_after = models.IntegerField(null=True, blank=True)
    date = models.DateField(default=timezone.now, db_index=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Stock Transaction'
        verbose_name_plural = 'Stock Transactions'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.date} - {self.product.name} - {self.get_transaction_type_display()} ({self.quantity})"


class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('ADD', 'Stock Addition (+)'),
        ('SUB', 'Stock Deduction (-)'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='adjustments')
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPES)
    quantity = models.PositiveIntegerField()
    date = models.DateField(default=timezone.now)
    reason = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Stock Adjustment'
        verbose_name_plural = 'Stock Adjustments'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Adj {self.adjustment_type} {self.quantity} on {self.product.name}"


class ProductPurchase(models.Model):
    STATUS_PAID = 'Paid'
    STATUS_UNPAID = 'Unpaid'
    STATUS_PARTIAL = 'Partially Paid'

    PAYMENT_STATUS_CHOICES = [
        (STATUS_PAID, 'Paid'),
        (STATUS_UNPAID, 'Unpaid'),
        (STATUS_PARTIAL, 'Partially Paid'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('UPI', 'UPI'),
        ('Cheque', 'Cheque'),
        ('Credit', 'Vendor Credit (To Pay Later)'),
        ('Other', 'Other'),
    ]

    purchase_number = models.CharField(max_length=50, unique=True, db_index=True)
    purchase_date = models.DateField(default=timezone.now, db_index=True)
    supplier_name = models.CharField(max_length=150)
    supplier_phone = models.CharField(max_length=20, blank=True, null=True)
    invoice_number = models.CharField(max_length=100, blank=True, null=True, help_text="Vendor Bill / Invoice #")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchases')
    quantity = models.PositiveIntegerField(help_text="Purchased quantity to add to factory inventory")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Cost per unit")
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=STATUS_PAID)
    vehicle_number = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Product Purchase'
        verbose_name_plural = 'Product Purchases'
        ordering = ['-purchase_date', '-created_at']

    def __str__(self):
        return f"{self.purchase_number} - {self.supplier_name} - {self.product.name} ({self.quantity})"

    def save(self, *args, **kwargs):
        if not self.total_amount or self.total_amount == 0:
            from decimal import Decimal
            self.total_amount = Decimal(str(self.quantity)) * self.unit_price
        super().save(*args, **kwargs)


from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Product)
def create_factory_inventory_for_product(sender, instance, created, **kwargs):
    if created:
        FactoryInventory.objects.get_or_create(product=instance)

