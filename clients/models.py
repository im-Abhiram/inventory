from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class Client(models.Model):
    PAYMENT_TYPE_CREDIT = 'Credit'
    PAYMENT_TYPE_CASH = 'Cash'

    PAYMENT_TYPE_CHOICES = [
        (PAYMENT_TYPE_CREDIT, 'Credit Client (Purchases on Credit with Limit)'),
        (PAYMENT_TYPE_CASH, 'Cash Client (Direct Payment / No Credit Line)'),
    ]

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True, db_index=True)
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default=PAYMENT_TYPE_CREDIT,
        help_text="Select whether client has a credit account or pays direct cash"
    )
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20)
    alt_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=150, blank=True, null=True)
    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Initial balance owed by client (+ for debt, - for credit)"
    )
    credit_limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('50000.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Maximum allowed outstanding credit"
    )
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code or 'No Code'})"

    def save(self, *args, **kwargs):
        # Auto-generate client code if left blank
        if not self.code or not self.code.strip():
            count = Client.objects.count() + 1
            code_candidate = f"CLT-{count:04d}"
            while Client.objects.filter(code=code_candidate).exists():
                count += 1
                code_candidate = f"CLT-{count:04d}"
            self.code = code_candidate
        else:
            self.code = self.code.strip().upper()

        if self.payment_type == self.PAYMENT_TYPE_CASH and (self.credit_limit is None or self.credit_limit == Decimal('50000.00')):
            self.credit_limit = Decimal('0.00')

        super().save(*args, **kwargs)

    @property
    def is_cash_client(self):
        return self.payment_type == self.PAYMENT_TYPE_CASH

    @property
    def financial_account(self):
        if hasattr(self, 'account'):
            return self.account
        return None

    @property
    def outstanding_balance(self):
        if hasattr(self, 'account'):
            return self.account.current_balance
        return self.opening_balance

    @property
    def available_credit(self):
        if self.is_cash_client:
            return Decimal('0.00')
        return self.credit_limit - self.outstanding_balance

    @property
    def is_credit_exceeded(self):
        if self.is_cash_client:
            return self.outstanding_balance > Decimal('0.00')
        return self.outstanding_balance > self.credit_limit
