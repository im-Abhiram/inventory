from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'code', 'description',
            'unit', 'selling_price', 'minimum_stock_level', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 6-inch Solid Brick'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BRK-SLD-6'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Technical specifications, composition, etc.'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'minimum_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 500'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        qs = Product.objects.filter(code__iexact=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Product with code '{code}' already exists.")
        return code
