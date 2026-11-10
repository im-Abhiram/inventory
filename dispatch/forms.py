from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.utils import timezone
from .models import Dispatch, DispatchItem
from clients.models import Client
from construction.models import ClientProject
from products.models import Product


class DispatchForm(forms.ModelForm):
    dispatch_date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    client = forms.ModelChoiceField(
        queryset=Client.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_client'})
    )
    project = forms.ModelChoiceField(
        queryset=ClientProject.objects.exclude(status='Cancelled').order_by('name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_project'}),
        help_text="Optional: Assign directly to a client construction site project"
    )
    vehicle_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. KL-07-CD-1234'})
    )
    driver_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Driver name & contact'})
    )
    delivery_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Delivery notes, site supervisor contact, etc.'})
    )

    class Meta:
        model = Dispatch
        fields = ['dispatch_date', 'client', 'project', 'vehicle_number', 'driver_name', 'delivery_notes']


class DispatchItemForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).select_related('inventory').order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select product-select'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control item-qty', 'placeholder': 'Qty'})
    )
    unit_price = forms.DecimalField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control item-price', 'step': '0.01', 'placeholder': 'Unit Price'})
    )

    class Meta:
        model = DispatchItem
        fields = ['product', 'quantity', 'unit_price']


class BaseDispatchItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        valid_items_count = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                valid_items_count += 1
                product = form.cleaned_data.get('product')
                qty = form.cleaned_data.get('quantity')
                if product and qty:
                    current_stock = product.inventory.current_stock
                    if qty > current_stock:
                        form.add_error(
                            'quantity',
                            f"Insufficient stock for '{product.name}'. Factory stock is only {current_stock} {product.unit}."
                        )

        if valid_items_count == 0:
            raise forms.ValidationError("At least one product item must be added to the dispatch.")


DispatchItemFormSet = inlineformset_factory(
    Dispatch,
    DispatchItem,
    form=DispatchItemForm,
    formset=BaseDispatchItemFormSet,
    extra=1,
    can_delete=True
)

