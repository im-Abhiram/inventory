from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from clients.models import Client
from products.models import Product
from construction.models import ClientProject


class Dispatch(models.Model):
    STATUS_UNPAID = 'Unpaid'
    STATUS_PARTIAL = 'Partially Paid'
    STATUS_PAID = 'Paid'

    PAYMENT_STATUS_CHOICES = [
        (STATUS_UNPAID, 'Unpaid'),
        (STATUS_PARTIAL, 'Partially Paid'),
        (STATUS_PAID, 'Paid'),
    ]

    dispatch_number = models.CharField(max_length=50, unique=True, db_index=True)
    dispatch_date = models.DateField(default=timezone.now, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='dispatches')
    project = models.ForeignKey(ClientProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispatches')
    vehicle_number = models.CharField(max_length=50, blank=True, null=True)
    driver_name = models.CharField(max_length=100, blank=True, null=True)
    delivery_notes = models.TextField(blank=True, null=True)
    
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    paid_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=STATUS_UNPAID,
        db_index=True
    )

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dispatch'
        verbose_name_plural = 'Dispatches'
        ordering = ['-dispatch_date', '-created_at']

    def __str__(self):
        return f"{self.dispatch_number} - {self.client.name} (₹{self.total_amount})"

    @property
    def outstanding_amount(self):
        balance = self.total_amount - self.paid_amount
        return max(Decimal('0.00'), balance)

    @property
    def total_quantity(self):
        total = self.items.aggregate(total=models.Sum('quantity'))['total']
        return total or 0

    def update_payment_status(self):
        if self.paid_amount >= self.total_amount and self.total_amount > Decimal('0.00'):
            self.payment_status = self.STATUS_PAID
        elif self.paid_amount > Decimal('0.00'):
            self.payment_status = self.STATUS_PARTIAL
        else:
            self.payment_status = self.STATUS_UNPAID
        self.save(update_fields=['paid_amount', 'payment_status'])


class DispatchItem(models.Model):
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='dispatch_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    class Meta:
        verbose_name = 'Dispatch Item'
        verbose_name_plural = 'Dispatch Items'

    def __str__(self):
        return f"{self.product.name} x {self.quantity} = ₹{self.total_price}"

    def save(self, *args, **kwargs):
        self.total_price = Decimal(str(self.quantity)) * self.unit_price
        super().save(*args, **kwargs)
