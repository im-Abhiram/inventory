from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.utils import timezone
from .models import ClientProject, DailyConstructionEntry, DailyMaterialUsage, ClientInventory
from clients.models import Client
from products.models import Product


class ClientProjectForm(forms.ModelForm):
    client = forms.ModelChoiceField(
        queryset=Client.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    expected_completion_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    actual_completion_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = ClientProject
        fields = [
            'client', 'name', 'location', 'start_date', 'expected_completion_date',
            'actual_completion_date', 'status', 'description', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Skyline Residency Tower A'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Site location / address'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Project scope, number of units, etc.'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'General notes'}),
        }


class DailyConstructionEntryForm(forms.ModelForm):
    date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    number_of_workers = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'})
    )
    work_progress_percentage = forms.IntegerField(
        min_value=0,
        max_value=100,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0-100'})
    )
    work_completed_today = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Work done today (e.g. Completed 1st floor masonry, boundary wall plastering)'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Weather delays, site inspections, contractor notes (optional)'})
    )

    class Meta:
        model = DailyConstructionEntry
        fields = ['date', 'number_of_workers', 'work_progress_percentage', 'work_completed_today', 'notes']


class DailyMaterialUsageForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select site-material-select'})
    )
    quantity_used = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Qty Used'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notes / area used'})
    )

    class Meta:
        model = DailyMaterialUsage
        fields = ['product', 'quantity_used', 'notes']


class BaseDailyMaterialUsageFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        if self.project:
            for form in self.forms:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    product = form.cleaned_data.get('product')
                    qty_used = form.cleaned_data.get('quantity_used')
                    if product and qty_used:
                        client_inv = ClientInventory.objects.filter(project=self.project, product=product).first()
                        available_stock = client_inv.current_stock if client_inv else 0
                        if qty_used > available_stock:
                            form.add_error(
                                'quantity_used',
                                f"Insufficient site stock for '{product.name}'. Site currently has only {available_stock} {product.unit} available."
                            )


DailyMaterialUsageFormSet = inlineformset_factory(
    DailyConstructionEntry,
    DailyMaterialUsage,
    form=DailyMaterialUsageForm,
    formset=BaseDailyMaterialUsageFormSet,
    extra=1,
    can_delete=True
)

