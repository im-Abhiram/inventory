import uuid
from django import forms
from django.utils import timezone
from .models import ProductionEntry
from products.models import Product


class ProductionEntryForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    production_date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2500'})
    )
    shift = forms.ChoiceField(
        choices=ProductionEntry.SHIFT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    worker_count = forms.IntegerField(
        min_value=1,
        initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Batch notes, raw material batch, machine notes (optional)'})
    )
    submission_token = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        model = ProductionEntry
        fields = ['production_date', 'product', 'quantity', 'shift', 'worker_count', 'notes', 'submission_token']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('submission_token'):
            self.fields['submission_token'].initial = uuid.uuid4().hex

