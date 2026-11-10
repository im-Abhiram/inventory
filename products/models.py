from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    UNIT_CHOICES = [
        ('Pieces', 'Pieces'),
        ('Numbers', 'Numbers'),
        ('Loads', 'Loads'),
        ('Bags', 'Bags'),
        ('Sq.Ft', 'Square Feet'),
        ('Tons', 'Tons'),
        ('Other', 'Other'),
    ]

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=30, choices=UNIT_CHOICES, default='Pieces')
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Standard selling price per unit"
    )
    minimum_stock_level = models.PositiveIntegerField(
        default=500,
        help_text="Alert threshold when stock drops below this value"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def current_stock(self):
        if hasattr(self, 'inventory'):
            return self.inventory.current_stock
        return 0

    @property
    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock_level
