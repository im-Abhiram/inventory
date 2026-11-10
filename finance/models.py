from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from clients.models import Client


class ClientAccount(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='account')
    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Opening balance owed by client"
    )
    total_dispatched = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_paid = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00')
    )
    adjustments = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00')
    )
    current_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00')
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Client Financial Account'
        verbose_name_plural = 'Client Financial Accounts'

    def __str__(self):
        return f"Account for {self.client.name} (Balance: ₹{self.current_balance})"

    def recalculate(self):
        """
        Recalculates balance from scratch:
        Outstanding Balance = Opening Balance + Total Dispatched - Total Paid + Adjustments
        """
        dispatches_sum = self.client.dispatches.aggregate(total=models.Sum('total_amount'))['total'] or Decimal('0.00')
        payments_sum = self.client.payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        self.total_dispatched = dispatches_sum
        self.total_paid = payments_sum
        self.current_balance = (self.opening_balance + self.total_dispatched - self.total_paid) + self.adjustments
        self.save()
        return self.current_balance


class Payment(models.Model):
    METHOD_CASH = 'Cash'
    METHOD_BANK = 'Bank Transfer'
    METHOD_UPI = 'UPI'
    METHOD_CHEQUE = 'Cheque'
    METHOD_OTHER = 'Other'

    METHOD_CHOICES = [
        (METHOD_CASH, 'Cash'),
        (METHOD_BANK, 'Bank Transfer'),
        (METHOD_UPI, 'UPI'),
        (METHOD_CHEQUE, 'Cheque'),
        (METHOD_OTHER, 'Other'),
    ]

    payment_number = models.CharField(max_length=50, unique=True, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='payments')
    payment_date = models.DateField(default=timezone.now, db_index=True)
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(max_length=30, choices=METHOD_CHOICES, default=METHOD_CASH)
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Cheque # / UPI UTR / Bank Ref")
    notes = models.TextField(blank=True, null=True)
    submission_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Client Payment'
        verbose_name_plural = 'Client Payments'
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"{self.payment_number} - {self.client.name} (₹{self.amount})"


class PaymentAllocation(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    dispatch = models.ForeignKey('dispatch.Dispatch', on_delete=models.CASCADE, related_name='payment_allocations')
    amount_allocated = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Payment Allocation'
        verbose_name_plural = 'Payment Allocations'

    def __str__(self):
        return f"{self.payment.payment_number} -> {self.dispatch.dispatch_number} (₹{self.amount_allocated})"


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Expense Category'
        verbose_name_plural = 'Expense Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('UPI', 'UPI'),
        ('Cheque', 'Cheque'),
        ('Other', 'Other'),
    ]

    expense_date = models.DateField(default=timezone.now, db_index=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"{self.expense_date} - {self.category.name}: ₹{self.amount}"


from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Client)
def create_client_account_for_client(sender, instance, created, **kwargs):
    if created:
        ClientAccount.objects.get_or_create(
            client=instance,
            defaults={
                'opening_balance': instance.opening_balance,
                'current_balance': instance.opening_balance
            }
        )

