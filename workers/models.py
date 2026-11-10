from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from construction.models import ClientProject


class Worker(models.Model):
    TYPE_MASON = 'Mason'
    TYPE_HELPER = 'Helper'
    TYPE_OPERATOR = 'Machine Operator'
    TYPE_DRIVER = 'Driver'
    TYPE_SUPERVISOR = 'Supervisor'
    TYPE_OTHER = 'Other'

    TYPE_CHOICES = [
        (TYPE_MASON, 'Mason'),
        (TYPE_HELPER, 'Helper'),
        (TYPE_OPERATOR, 'Machine Operator'),
        (TYPE_DRIVER, 'Driver'),
        (TYPE_SUPERVISOR, 'Supervisor'),
        (TYPE_OTHER, 'Other'),
    ]

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, null=True)
    worker_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default=TYPE_HELPER)
    joining_date = models.DateField(default=timezone.now)
    daily_wage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Worker'
        verbose_name_plural = 'Workers'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_worker_type_display()})"


class WorkerAttendance(models.Model):
    STATUS_PRESENT = 'Present'
    STATUS_ABSENT = 'Absent'
    STATUS_HALF_DAY = 'Half Day'

    STATUS_CHOICES = [
        (STATUS_PRESENT, 'Present'),
        (STATUS_ABSENT, 'Absent'),
        (STATUS_HALF_DAY, 'Half Day'),
    ]

    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=timezone.now, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PRESENT)
    project = models.ForeignKey(ClientProject, on_delete=models.SET_NULL, null=True, blank=True, related_name='worker_attendances')
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Worker Attendance'
        verbose_name_plural = 'Worker Attendances'
        ordering = ['-date', 'worker__name']
        unique_together = ('worker', 'date')

    def __str__(self):
        return f"{self.worker.name} - {self.date}: {self.status}"
