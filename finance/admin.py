from django.contrib import admin
from .models import ClientAccount, Payment, PaymentAllocation, Expense, ExpenseCategory


@admin.register(ClientAccount)
class ClientAccountAdmin(admin.ModelAdmin):
    list_display = ('client', 'opening_balance', 'total_dispatched', 'total_paid', 'current_balance')
    search_fields = ('client__name', 'client__code')


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 1


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_number', 'payment_date', 'client', 'amount', 'payment_method', 'recorded_by')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('payment_number', 'client__name', 'reference_number')
    inlines = [PaymentAllocationInline]


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('expense_date', 'category', 'description', 'amount', 'payment_method', 'recorded_by')
    list_filter = ('category', 'expense_date', 'payment_method')
    search_fields = ('description', 'reference_number')
