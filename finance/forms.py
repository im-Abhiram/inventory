import uuid
from django import forms
from django.utils import timezone
from .models import Payment, PaymentAllocation, Expense, ExpenseCategory
from clients.models import Client
from dispatch.models import Dispatch


class PaymentForm(forms.ModelForm):
    payment_date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    client = forms.ModelChoiceField(
        queryset=Client.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_client'})
    )
    amount = forms.DecimalField(
        min_value=0.01,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'})
    )
    payment_method = forms.ChoiceField(
        choices=Payment.METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    reference_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction ID / Cheque # / UPI UTR'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notes (optional)'})
    )
    submission_token = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        model = Payment
        fields = ['client', 'payment_date', 'amount', 'payment_method', 'reference_number', 'notes', 'submission_token']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('submission_token'):
            self.fields['submission_token'].initial = uuid.uuid4().hex


class ExpenseForm(forms.ModelForm):
    expense_date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    description = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Diesel for generator 50L'})
    )
    amount = forms.DecimalField(
        min_value=0.01,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'})
    )
    payment_method = forms.ChoiceField(
        choices=Expense.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    reference_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Voucher # / Bill # / Ref'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Vendor name, invoice details (optional)'})
    )

    class Meta:
        model = Expense
        fields = ['expense_date', 'category', 'description', 'amount', 'payment_method', 'reference_number', 'notes']


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Description (optional)'}),
        }

