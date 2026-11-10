from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'phone', 'contact_person', 'opening_balance', 'credit_limit', 'is_active')
    search_fields = ('name', 'code', 'phone')
    list_filter = ('is_active',)
