from django.contrib import admin
from .models import Dispatch, DispatchItem


class DispatchItemInline(admin.TabularInline):
    model = DispatchItem
    extra = 1


@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    list_display = ('dispatch_number', 'dispatch_date', 'client', 'project', 'total_amount', 'paid_amount', 'payment_status')
    list_filter = ('payment_status', 'dispatch_date')
    search_fields = ('dispatch_number', 'client__name', 'vehicle_number')
    inlines = [DispatchItemInline]
