from django.contrib import admin
from .models import Worker, WorkerAttendance


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'worker_type', 'daily_wage', 'is_active')
    list_filter = ('worker_type', 'is_active')
    search_fields = ('name', 'phone')


@admin.register(WorkerAttendance)
class WorkerAttendanceAdmin(admin.ModelAdmin):
    list_display = ('date', 'worker', 'status', 'project', 'recorded_by')
    list_filter = ('status', 'date')
    search_fields = ('worker__name',)
