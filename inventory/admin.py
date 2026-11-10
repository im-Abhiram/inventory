from django.contrib import admin
from .models import FactoryInventory, StockTransaction, StockAdjustment


@admin.register(FactoryInventory)
class FactoryInventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'opening_stock', 'total_production', 'total_additions', 'total_dispatch', 'current_stock', 'stock_status')
    search_fields = ('product__name', 'product__code')


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'product', 'transaction_type', 'quantity', 'balance_after', 'reference', 'created_by')
    list_filter = ('transaction_type', 'date')
    search_fields = ('product__name', 'reference', 'notes')


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('date', 'product', 'adjustment_type', 'quantity', 'reason', 'created_by')
    list_filter = ('adjustment_type', 'date')
