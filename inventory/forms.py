from django import forms
from django.utils import timezone
from .models import StockAdjustment
from products.models import Product


class StockAdjustmentForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).select_related('inventory'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    adjustment_type = forms.ChoiceField(
        choices=StockAdjustment.ADJUSTMENT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter quantity'})
    )
    date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for adjustment (e.g. Broken during handling, Physical audit discrepancy, Opening stock correction)'})
    )

    class Meta:
        model = StockAdjustment
        fields = ['product', 'adjustment_type', 'quantity', 'date', 'reason']

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        adjustment_type = cleaned_data.get('adjustment_type')
        quantity = cleaned_data.get('quantity')

        if product and adjustment_type == 'SUB' and quantity:
            current_stock = product.inventory.current_stock
            if quantity > current_stock:
                self.add_error(
                    'quantity',
                    f"Cannot deduct {quantity} units. Current factory stock is only {current_stock} units."
                )

        return cleaned_data




from .models import ProductPurchase


class ProductPurchaseForm(forms.ModelForm):
    purchase_date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_purchase_product'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_purchase_qty', 'placeholder': 'e.g. 1000'})
    )
    unit_price = forms.DecimalField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_purchase_price', 'placeholder': '0.00'})
    )
    supplier_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vendor / Supplier Company Name'})
    )
    supplier_phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210'})
    )
    invoice_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bill / Tax Invoice No.'})
    )
    vehicle_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Delivery vehicle reg. no.'})
    )
    payment_method = forms.ChoiceField(
        choices=ProductPurchase.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_status = forms.ChoiceField(
        choices=ProductPurchase.PAYMENT_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Delivery notes, quality check notes (optional)'})
    )

    class Meta:
        model = ProductPurchase
        fields = [
            'purchase_date', 'supplier_name', 'supplier_phone', 'invoice_number',
            'product', 'quantity', 'unit_price', 'payment_method', 'payment_status',
            'vehicle_number', 'notes'
        ]
