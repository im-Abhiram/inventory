from django.contrib import admin
from .models import ProductionEntry


@admin.register(ProductionEntry)
class ProductionEntryAdmin(admin.ModelAdmin):
    list_display = ('production_date', 'product', 'quantity', 'shift', 'worker_count', 'created_by')
    list_filter = ('shift', 'production_date', 'product')
    search_fields = ('product__name', 'notes')
