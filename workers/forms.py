from django import forms
from django.utils import timezone
from .models import Worker, WorkerAttendance
from construction.models import ClientProject


class WorkerForm(forms.ModelForm):
    joining_date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = Worker
        fields = ['name', 'phone', 'worker_type', 'joining_date', 'daily_wage', 'is_active', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Worker Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210'}),
            'worker_type': forms.Select(attrs={'class': 'form-select'}),
            'daily_wage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Skills, emergency contact, etc.'}),
        }


class WorkerAttendanceForm(forms.ModelForm):
    date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    worker = forms.ModelChoiceField(
        queryset=Worker.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=WorkerAttendance.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    project = forms.ModelChoiceField(
        queryset=ClientProject.objects.exclude(status='Cancelled').order_by('name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Optional: If assigned to a client construction site today"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional notes'})
    )

    class Meta:
        model = WorkerAttendance
        fields = ['worker', 'date', 'status', 'project', 'notes']

