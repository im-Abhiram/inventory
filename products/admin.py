from django.contrib import admin
from .models import ProductCategory, Product


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'unit', 'selling_price', 'minimum_stock_level', 'is_active')
    list_filter = ('category', 'unit', 'is_active')
    search_fields = ('name', 'code')
