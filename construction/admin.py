from django.contrib import admin
from .models import ClientProject, ClientInventory, ClientStockTransaction, DailyConstructionEntry, DailyMaterialUsage


class DailyMaterialUsageInline(admin.TabularInline):
    model = DailyMaterialUsage
    extra = 1


@admin.register(ClientProject)
class ClientProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'client', 'location', 'start_date', 'status')
    list_filter = ('status', 'start_date')
    search_fields = ('name', 'client__name', 'location')


@admin.register(ClientInventory)
class ClientInventoryAdmin(admin.ModelAdmin):
    list_display = ('project', 'product', 'opening_stock', 'total_received', 'total_used', 'current_stock')
    list_filter = ('product',)
    search_fields = ('project__name', 'product__name')


@admin.register(DailyConstructionEntry)
class DailyConstructionEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'project', 'number_of_workers', 'work_progress_percentage', 'created_by')
    list_filter = ('date', 'project')
    inlines = [DailyMaterialUsageInline]


@admin.register(ClientStockTransaction)
class ClientStockTransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'project', 'product', 'transaction_type', 'quantity', 'balance_after', 'created_by')
    list_filter = ('transaction_type', 'date')
