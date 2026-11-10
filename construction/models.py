from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from clients.models import Client
from products.models import Product


class ClientProject(models.Model):
    STATUS_PLANNING = 'Planning'
    STATUS_ACTIVE = 'Active'
    STATUS_ON_HOLD = 'On Hold'
    STATUS_COMPLETED = 'Completed'
    STATUS_CANCELLED = 'Cancelled'

    STATUS_CHOICES = [
        (STATUS_PLANNING, 'Planning'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ON_HOLD, 'On Hold'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=200, blank=True, null=True)
    start_date = models.DateField(default=timezone.now)
    expected_completion_date = models.DateField(blank=True, null=True)
    actual_completion_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Client Construction Project'
        verbose_name_plural = 'Client Construction Projects'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.client.name}"

    @property
    def latest_progress(self):
        latest = self.daily_entries.order_by('-date', '-created_at').first()
        return latest.work_progress_percentage if latest else 0

    @property
    def total_worker_days(self):
        total = self.daily_entries.aggregate(total=models.Sum('number_of_workers'))['total']
        return total or 0


class ClientInventory(models.Model):
    project = models.ForeignKey(ClientProject, on_delete=models.CASCADE, related_name='material_inventories')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='client_inventories')
    opening_stock = models.PositiveIntegerField(default=0)
    total_received = models.PositiveIntegerField(default=0)
    total_used = models.PositiveIntegerField(default=0)
    current_stock = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Client Material Inventory'
        verbose_name_plural = 'Client Material Inventories'
        unique_together = ('project', 'product')

    def __str__(self):
        return f"{self.project.name} | {self.product.name} (Stock: {self.current_stock})"

    def recalculate(self):
        self.current_stock = (self.opening_stock + self.total_received) - self.total_used
        return self.current_stock


class ClientStockTransaction(models.Model):
    TYPE_OPENING = 'OPENING'
    TYPE_RECEIVED = 'RECEIVED'
    TYPE_USAGE = 'USAGE'
    TYPE_ADJUSTMENT_ADD = 'ADJUSTMENT_ADD'
    TYPE_ADJUSTMENT_SUB = 'ADJUSTMENT_SUB'
    TYPE_USAGE_REVERSAL = 'USAGE_REVERSAL'

    TRANSACTION_TYPES = [
        (TYPE_OPENING, 'Opening Stock'),
        (TYPE_RECEIVED, 'Dispatched / Received'),
        (TYPE_USAGE, 'Construction Usage (-)'),
        (TYPE_ADJUSTMENT_ADD, 'Stock Adjustment (+)'),
        (TYPE_ADJUSTMENT_SUB, 'Stock Adjustment (-)'),
        (TYPE_USAGE_REVERSAL, 'Usage Reversal (+)'),
    ]

    project = models.ForeignKey(ClientProject, on_delete=models.CASCADE, related_name='stock_transactions')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='client_stock_transactions')
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES, db_index=True)
    quantity = models.PositiveIntegerField()
    balance_after = models.IntegerField(null=True, blank=True)
    date = models.DateField(default=timezone.now, db_index=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Client Stock Transaction'
        verbose_name_plural = 'Client Stock Transactions'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.product.name} - {self.get_transaction_type_display()} ({self.quantity})"


class DailyConstructionEntry(models.Model):
    project = models.ForeignKey(ClientProject, on_delete=models.CASCADE, related_name='daily_entries')
    date = models.DateField(default=timezone.now, db_index=True)
    number_of_workers = models.PositiveIntegerField(default=0, help_text="Number of workers present today")
    work_completed_today = models.TextField(blank=True, null=True, help_text="Summary of work completed")
    work_progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Estimated overall project progress (0-100%)"
    )
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Daily Construction Entry'
        verbose_name_plural = 'Daily Construction Entries'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.date} (Workers: {self.number_of_workers})"


class DailyMaterialUsage(models.Model):
    entry = models.ForeignKey(DailyConstructionEntry, on_delete=models.CASCADE, related_name='material_usages')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='construction_usages')
    quantity_used = models.PositiveIntegerField()
    unit = models.CharField(max_length=30, default='Pieces')
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Daily Material Usage'
        verbose_name_plural = 'Daily Material Usages'

    def __str__(self):
        return f"{self.entry.date} - {self.product.name}: {self.quantity_used} {self.unit}"
