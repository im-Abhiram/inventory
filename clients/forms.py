from django import forms
from .models import Client


class ClientForm(forms.ModelForm):
    code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional (Leave blank to auto-generate)'})
    )

    class Meta:
        model = Client
        fields = [
            'name', 'code', 'payment_type', 'contact_person', 'phone', 'alt_phone',
            'location', 'address', 'opening_balance', 'credit_limit', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Skyline Builders Pvt Ltd'}),
            'payment_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_type'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Mr. Rajesh Kumar'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210'}),
            'alt_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional alternate number'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, District, Area'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full billing / office address'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_credit_limit', 'placeholder': '50000.00'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Special pricing notes, delivery instructions, etc.'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code or not code.strip():
            return ''
        code = code.strip().upper()
        qs = Client.objects.filter(code__iexact=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Client code '{code}' is already registered.")
        return code
