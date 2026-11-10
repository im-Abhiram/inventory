from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Worker, WorkerAttendance
from .forms import WorkerForm, WorkerAttendanceForm
from construction.models import ClientProject
from accounts.decorators import superadmin_required


@login_required
def worker_list(request):
    search_query = request.GET.get('q', '').strip()
    type_filter = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()

    workers = Worker.objects.all().order_by('name')

    if search_query:
        workers = workers.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    if type_filter:
        workers = workers.filter(worker_type=type_filter)

    if status_filter == 'active':
        workers = workers.filter(is_active=True)
    elif status_filter == 'inactive':
        workers = workers.filter(is_active=False)

    paginator = Paginator(workers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'workers/worker_list.html', {
        'page_obj': page_obj,
        'types': Worker.TYPE_CHOICES,
        'search_query': search_query,
        'selected_type': type_filter,
        'selected_status': status_filter,
    })


@superadmin_required
def worker_create(request):
    if request.method == 'POST':
        form = WorkerForm(request.POST)
        if form.is_valid():
            worker = form.save()
            messages.success(request, f"Worker '{worker.name}' added successfully.")
            return redirect('workers:worker_list')
    else:
        form = WorkerForm()

    return render(request, 'workers/worker_form.html', {
        'form': form,
        'title': 'Add New Worker'
    })


@superadmin_required
def worker_edit(request, worker_id):
    worker = get_object_or_404(Worker, id=worker_id)
    if request.method == 'POST':
        form = WorkerForm(request.POST, instance=worker)
        if form.is_valid():
            form.save()
            messages.success(request, f"Worker '{worker.name}' updated successfully.")
            return redirect('workers:worker_list')
    else:
        form = WorkerForm(instance=worker)

    return render(request, 'workers/worker_form.html', {
        'form': form,
        'title': f'Edit Worker: {worker.name}',
        'worker': worker
    })


@superadmin_required
def worker_toggle_status(request, worker_id):
    if request.method == 'POST':
        worker = get_object_or_404(Worker, id=worker_id)
        worker.is_active = not worker.is_active
        worker.save(update_fields=['is_active'])
        status_text = "activated" if worker.is_active else "deactivated"
        messages.success(request, f"Worker '{worker.name}' was {status_text}.")
    return redirect('workers:worker_list')


@login_required
def attendance_list(request):
    date_filter = request.GET.get('date', timezone.now().strftime('%Y-%m-%d'))
    project_id = request.GET.get('project', '').strip()
    status_filter = request.GET.get('status', '').strip()

    attendances = WorkerAttendance.objects.select_related('worker', 'project', 'recorded_by').filter(date=date_filter)

    if project_id:
        attendances = attendances.filter(project_id=project_id)

    if status_filter:
        attendances = attendances.filter(status=status_filter)

    projects = ClientProject.objects.exclude(status='Cancelled').order_by('name')

    # Stats for the day
    present_count = attendances.filter(status=WorkerAttendance.STATUS_PRESENT).count()
    half_day_count = attendances.filter(status=WorkerAttendance.STATUS_HALF_DAY).count()
    absent_count = attendances.filter(status=WorkerAttendance.STATUS_ABSENT).count()

    return render(request, 'workers/attendance_list.html', {
        'attendances': attendances,
        'projects': projects,
        'statuses': WorkerAttendance.STATUS_CHOICES,
        'selected_date': date_filter,
        'selected_project': project_id,
        'selected_status': status_filter,
        'present_count': present_count,
        'half_day_count': half_day_count,
        'absent_count': absent_count,
    })


@superadmin_required
def attendance_record(request):
    selected_date_str = request.POST.get('date', request.GET.get('date', timezone.now().strftime('%Y-%m-%d')))
    active_workers = Worker.objects.filter(is_active=True).order_by('name')
    projects = ClientProject.objects.exclude(status='Cancelled').order_by('name')

    # Existing attendances for this date
    existing_attendance = {
        att.worker_id: att
        for att in WorkerAttendance.objects.filter(date=selected_date_str)
    }

    if request.method == 'POST' and 'save_bulk' in request.POST:
        with transaction.atomic():
            for worker in active_workers:
                status_val = request.POST.get(f'status_{worker.id}')
                project_id = request.POST.get(f'project_{worker.id}')
                notes_val = request.POST.get(f'notes_{worker.id}', '').strip()

                if status_val:
                    proj = ClientProject.objects.filter(id=project_id).first() if project_id else None
                    WorkerAttendance.objects.update_or_create(
                        worker=worker,
                        date=selected_date_str,
                        defaults={
                            'status': status_val,
                            'project': proj,
                            'notes': notes_val,
                            'recorded_by': request.user,
                        }
                    )
            messages.success(request, f"Attendance for {selected_date_str} saved successfully.")
            return redirect(f"{redirect('workers:attendance_list').url}?date={selected_date_str}")

    worker_rows = []
    for worker in active_workers:
        existing = existing_attendance.get(worker.id)
        worker_rows.append({
            'worker': worker,
            'status': existing.status if existing else WorkerAttendance.STATUS_PRESENT,
            'project_id': existing.project_id if existing and existing.project_id else '',
            'notes': existing.notes if existing else '',
        })

    return render(request, 'workers/attendance_record.html', {
        'selected_date': selected_date_str,
        'worker_rows': worker_rows,
        'projects': projects,
    })
