from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from products.models import Product


class ProductionEntry(models.Model):
    SHIFT_MORNING = 'Morning'
    SHIFT_AFTERNOON = 'Afternoon'
    SHIFT_NIGHT = 'Night'
    SHIFT_OTHER = 'Other'

    SHIFT_CHOICES = [
        (SHIFT_MORNING, 'Morning'),
        (SHIFT_AFTERNOON, 'Afternoon'),
        (SHIFT_NIGHT, 'Night'),
        (SHIFT_OTHER, 'Other'),
    ]

    production_date = models.DateField(default=timezone.now, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='production_entries')
    quantity = models.PositiveIntegerField(help_text="Quantity produced")
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, default=SHIFT_MORNING)
    worker_count = models.PositiveIntegerField(default=1, help_text="Number of workers on shift")
    notes = models.TextField(blank=True, null=True)
    submission_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Production Entry'
        verbose_name_plural = 'Production Entries'
        ordering = ['-production_date', '-created_at']

    def __str__(self):
        return f"{self.production_date} - {self.product.name}: {self.quantity} ({self.shift})"
